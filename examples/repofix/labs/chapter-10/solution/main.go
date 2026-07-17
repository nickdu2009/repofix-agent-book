// LAB:chapter-10 STATUS:complete
// Go 1.26: encode legal state transitions in program-owned data.
package main

import "fmt"

type RunStatus string

const (
	Pending RunStatus = "pending"
	Running RunStatus = "running"
	Failed  RunStatus = "failed"
)

func canTransition(from, to RunStatus) bool {
	allowed := map[RunStatus]map[RunStatus]bool{
		Pending: {Running: true},
		Running: {Failed: true},
	}
	return allowed[from][to]
}

func main() {
	if !canTransition(Pending, Running) || canTransition(Failed, Running) {
		panic("transition policy failed")
	}
	fmt.Println("chapter-10: PASS")
}
