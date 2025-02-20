package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"regexp"
	"strconv"

	"github.com/bwmarrin/snowflake"
)

// nodeName, podName, podUID are injected into the container by Kubernetes
// nodeName, podUID are just for dubugging
// podName is used to extract the machine ID


var (
    node       *snowflake.Node
	nodeName   string
    podUID     string
	podName	string
    machineID  int
)

func main() {
    
    nodeName = os.Getenv("NODE_NAME")
    podUID = os.Getenv("POD_UID")

    // Get POD_NAME or use default
	podName = os.Getenv("POD_NAME")
    if podName == "" {
        podName = "id-generator-1023"
    }


    // Extract numeric part from POD_NAME for machine ID
    re := regexp.MustCompile(`\d+`)
    match := re.FindString(podName)
    if match == "" {
        log.Fatalf("Failed to find a numeric part in POD_NAME: %s", podName)
    }

    var err error
    machineID, err = strconv.Atoi(match)
    if err != nil {
        log.Fatalf("Invalid machine ID extracted from POD_NAME: %v", err)
    }

    // Set the custom epoch in milliseconds.
    // (Python value is in seconds, so multiply by 1000.)
    snowflake.Epoch = 1739526270 * 1000 // 2025-02-14 15:13:00 UTC

    // Create a Snowflake node
    node, err = snowflake.NewNode(int64(machineID))
    if err != nil {
        log.Fatalf("Failed to create snowflake node: %v", err)
    }


    // HTTP routes
    http.HandleFunc("/health", healthHandler)
    http.HandleFunc("/generate-id", generateIDHandler)

    log.Println("Starting server on :8000...")
    if err := http.ListenAndServe(":8000", nil); err != nil {
        log.Fatalf("Server failed: %v", err)
    }
}

// healthHandler returns basic health and metadata info
func healthHandler(w http.ResponseWriter, r *http.Request) {
    enableCORS(&w)
    w.Header().Set("Content-Type", "application/json")

    resp := map[string]interface{}{
        "status":     "OK",
		"machine_id": machineID,
		"pod_uid": podUID,
		"node_name": nodeName,
		"pod_name": podName,
        "language":  "Go",
    }
    _ = json.NewEncoder(w).Encode(resp)
}

// generateIDHandler returns the next snowflake integer ID
func generateIDHandler(w http.ResponseWriter, r *http.Request) {
    enableCORS(&w)
    w.Header().Set("Content-Type", "application/json")

    id := node.Generate().Int64()
    resp := map[string]interface{}{
        "id": id,
    }
    _ = json.NewEncoder(w).Encode(resp)
}

// enableCORS adds CORS headers to the response
func enableCORS(w *http.ResponseWriter) {
    (*w).Header().Set("Access-Control-Allow-Origin", "*")
    (*w).Header().Set("Access-Control-Allow-Credentials", "true")
    (*w).Header().Set("Access-Control-Allow-Methods", "*")
    (*w).Header().Set("Access-Control-Allow-Headers", "*")
}
