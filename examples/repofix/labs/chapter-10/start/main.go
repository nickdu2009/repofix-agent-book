// LAB:chapter-10 STATUS:todo
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
	// TODO: permit Pending -> Running and Running -> Failed only.
	return true
}

func main() {
	if !canTransition(Pending, Running) || canTransition(Failed, Running) {
		panic("transition policy failed")
	}
	fmt.Println("chapter-10: PASS")
}
