package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"html/template"
	"io/ioutil"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	log "github.com/sirupsen/logrus"
	"github.com/fatih/structs"
	"github.com/gorilla/mux"
	"github.com/malice-plugins/pkgs/database"
	"github.com/malice-plugins/pkgs/database/elasticsearch"
	"github.com/malice-plugins/pkgs/utils"
	"github.com/parnurzeal/gorequest"
	"github.com/pkg/errors"
	"github.com/urfave/cli"
)

const (
	name     = "clamav"
	category = "av"
)

var (
	// Version stores the plugin's version
	Version string
	// BuildTime stores the plugin's build time
	BuildTime string

	path string

	// es is the elasticsearch database object
	es elasticsearch.Database
)

type pluginResults struct {
	ID   string      `json:"id" structs:"id,omitempty"`
	Data ResultsData `json:"clamav" structs:"clamav"`
}

// ClamAV json object
type ClamAV struct {
	Results ResultsData `json:"clamav"`
}

// ResultsData json object
type ResultsData struct {
	Infected bool   `json:"infected" structs:"infected"`
	Result   string `json:"result" structs:"result"`
	Engine   string `json:"engine" structs:"engine"`
	Known    string `json:"known" structs:"known"`
	Updated  string `json:"updated" structs:"updated"`
	Error    string `json:"error" structs:"error"`
	MarkDown string `json:"markdown,omitempty" structs:"markdown,omitempty"`
}

func assert(err error) {
	if err != nil {
		// ClamAV exits with error status 1 if it finds a virus
		if err.Error() != "exit status 1" {
			log.WithFields(log.Fields{
				"plugin":   name,
				"category": category,
				"path":     path,
			}).Fatal(err)
		}
	}
}

// RunCommand runs cmd on file
func RunCommand(ctx context.Context, cmd string, args ...string) (string, error) {

	var c *exec.Cmd

	if ctx != nil {
		c = exec.CommandContext(ctx, cmd, args...)
	} else {
		c = exec.Command(cmd, args...)
	}

	output, err := c.CombinedOutput()
	if err != nil {
		return string(output), err
	}

	// check for exec context timeout
	if ctx != nil {
		if ctx.Err() == context.DeadlineExceeded {
			return "", fmt.Errorf("command %s timed out", cmd)
		}
	}

	return string(output), nil
}

// AvScan performs antivirus scan
func AvScan(timeout int) ClamAV {

	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeout)*time.Second)
	defer cancel()

	results, err := utils.RunCommand(ctx, "/usr/bin/clamscan", "--stdout", path)
	assert(err)

	return ClamAV{
		Results: ParseClamAvOutput(results, nil),
	}
}

// ParseClamAvOutput convert clamav output into ClamAV struct
func ParseClamAvOutput(clamout string, err error) ResultsData {

	if err != nil {
		return ResultsData{Error: err.Error()}
	}

	log.WithFields(log.Fields{
		"plugin":   name,
		"category": category,
		"path":     path,
	}).Debug("ClamAV Output: ", clamout)

	clamAV := ResultsData{}

	lines := strings.Split(clamout, "\n")
	// Extract AV Scan Result
	result := lines[0]
	if len(result) != 0 {
		pathAndResult := strings.Split(result, ":")
		if strings.Contains(pathAndResult[1], "OK") {
			clamAV.Infected = false
		} else {
			clamAV.Infected = true
			clamAV.Result = strings.TrimSpace(strings.TrimRight(pathAndResult[1], "FOUND"))
		}
	} else {
		fmt.Println("[ERROR] empty scan result: ", result)
		os.Exit(2)
	}
	// Extract Clam Details from SCAN SUMMARY
	for _, line := range lines[1:] {
		if len(line) != 0 {
			keyvalue := strings.Split(line, ":")
			if len(keyvalue) != 0 {
				switch {
				case strings.Contains(keyvalue[0], "Known viruses"):
					clamAV.Known = strings.TrimSpace(keyvalue[1])
				case strings.Contains(line, "Engine version"):
					clamAV.Engine = strings.TrimSpace(keyvalue[1])
				}
			}
		}
	}

	clamAV.Updated = getUpdatedDate()

	return clamAV
}

func updateAV(ctx context.Context) error {
	fmt.Println("Updating ClamAV...")
	fmt.Println(utils.RunCommand(ctx, "freshclam"))
	// Update UPDATED file
	t := time.Now().Format("20060102")
	err := ioutil.WriteFile("/opt/malice/UPDATED", []byte(t), 0644)
	return err
}

func getUpdatedDate() string {
	if _, err := os.Stat("/opt/malice/UPDATED"); os.IsNotExist(err) {
		return BuildTime
	}
	updated, err := ioutil.ReadFile("/opt/malice/UPDATED")
	assert(err)
	return string(updated)
}

func generateMarkDownTable(c ClamAV) string {
	var tplOut bytes.Buffer

	t := template.Must(template.New("comodo").Parse(tpl))

	err := t.Execute(&tplOut, c)
	if err != nil {
		log.Println("executing template:", err)
	}

	return tplOut.String()
}

func printStatus(resp gorequest.Response, body string, errs []error) {
	fmt.Println(body)
}

func webService() {
	router := mux.NewRouter().StrictSlash(true)
	router.HandleFunc("/scan", webAvScan).Methods("POST")
	log.Info("web service listening on port :3993")
	log.Fatal(http.ListenAndServe(":3993", router))
}

func webAvScan(w http.ResponseWriter, r *http.Request) {

	r.ParseMultipartForm(32 << 20)
	file, header, err := r.FormFile("malware")
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		fmt.Fprintln(w, "Please supply a valid file to scan.")
		log.Error(err)
	}
	defer file.Close()

	log.Debug("Uploaded fileName: ", header.Filename)

	tmpfile, err := ioutil.TempFile("/malware", "web_")
	if err != nil {
		log.Fatal(err)
	}
	defer os.Remove(tmpfile.Name()) // clean up

	data, err := ioutil.ReadAll(file)
	assert(err)

	if _, err = tmpfile.Write(data); err != nil {
		log.Fatal(err)
	}
	if err = tmpfile.Close(); err != nil {
		log.Fatal(err)
	}

	// Do AV scan
	path = tmpfile.Name()
	clamav := AvScan(60)

	w.Header().Set("Content-Type", "application/json; charset=UTF-8")
	w.WriteHeader(http.StatusOK)

	if err := json.NewEncoder(w).Encode(clamav); err != nil {
		log.Fatal(err)
	}
}

func main() {

	cli.AppHelpTemplate = utils.AppHelpTemplate
	app := cli.NewApp()

	app.Name = "clamav"
	app.Version = Version + ", BuildTime: " + BuildTime
	app.Compiled, _ = time.Parse("20060102", BuildTime)
	app.Usage = "Malice ClamAV Plugin"
	// flags start here
	app.Flags = []cli.Flag {
		&cli.BoolFlag{Name: "verbose, V", Usage: "verbose output"},
		&cli.BoolFlag{Name: "table, t", Usage: "output as Markdown table"},
		&cli.BoolFlag{Name: "callback, c", Usage: "POST results to Malice webhook"},
		&cli.BoolFlag{Name: "proxy, x", Usage: "proxy settings for Malice webhook endpoint"},
		&cli.StringFlag{Name: "elasticsearch", Value: "", Usage: "elasticsearch url for Malice to store results"},
		&cli.IntFlag{Name: "timeout", Value: 60, Usage: "malice plugin timeout (in seconds)"},
	}
	timeout := 60
	app.Commands = []*cli.Command{
		{
			Name:    "update",
			Aliases: []string{"u"},
			Usage:   "Update virus definitions",
			Action: func(c *cli.Context) error {
				ctx, cancel := context.WithTimeout(
					context.Background(),
					time.Duration(timeout)*time.Second,
				)
				defer cancel()

				return updateAV(ctx)
			},
		},
		{
			Name:  "web",
			Usage: "Create a ClamAV scan web service",
			Action: func(c *cli.Context) error {
				webService()
				return nil
			},
		},
	}
	app.Action = func(c *cli.Context) error {

		var err error

		if c.Bool("verbose") {
			log.SetLevel(log.DebugLevel)
		}

		if c.Args().Present() {
			path, err = filepath.Abs(c.Args().First())
			assert(err)

			if _, err = os.Stat(path); os.IsNotExist(err) {
				assert(err)
			}

			clamav := AvScan(c.Int("timeout"))
			clamav.Results.MarkDown = generateMarkDownTable(clamav)

			// upsert into Database
			if len(c.String("elasticsearch")) > 0 {
				err := es.Init()
				if err != nil {
					return errors.Wrap(err, "failed to initalize elasticsearch")
				}
				err = es.StorePluginResults(database.PluginResults{
					ID:       utils.Getopt("MALICE_SCANID", utils.GetSHA256(path)),
					Name:     name,
					Category: category,
					Data:     structs.Map(clamav.Results),
				})
				if err != nil {
					return errors.Wrapf(err, "failed to index malice/%s results", name)
				}
			}

			if c.Bool("table") {
				fmt.Println(clamav.Results.MarkDown)
			} else {
				// convert to JSON
				clamav.Results.MarkDown = ""
				clamavJSON, err := json.Marshal(clamav)
				assert(err)
				if c.Bool("post") {
					request := gorequest.New()
					if c.Bool("proxy") {
						request = gorequest.New().Proxy(os.Getenv("MALICE_PROXY"))
					}
					request.Post(os.Getenv("MALICE_ENDPOINT")).
						Set("X-Malice-ID", utils.Getopt("MALICE_SCANID", utils.GetSHA256(path))).
						Send(string(clamavJSON)).
						End(printStatus)

					return nil
				}
				fmt.Println(string(clamavJSON))
			}
		} else {
			log.Fatal(fmt.Errorf("Please supply a file to scan with malice/clamav"))
		}
		return nil
	}

	err := app.Run(os.Args)
	assert(err)
}
