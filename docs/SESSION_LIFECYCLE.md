# Session/dialogue lifecycle — V1

A dialogue represents one maintenance task/context. Codex thread is history authority; controller keeps only reliability metadata/transient content.

## NO_DIALOGUE
Profile/model/reasoning defaults may change. NEW DIALOGUE does not create empty disk state; next accepted group prompt lazily creates the thread.

## Lazy create
Persist ingress/create intent -> capture profile -> ensure profile app-server/capabilities -> validate model/effort -> thread/start -> persist exact binding -> turn/start. Ambiguous creation enters CREATE_UNKNOWN and is not repeated blindly.

## IDLE dialogue
Thread/profile stay bound. Next prompt uses exact thread. Model/reasoning may change for next turn after runtime validation; profile cannot change until hard delete.

## TURN_RUNNING
Snapshot immutable. New prompts receive BUSY and are not queued. Execution settings changes are blocked. Operator may request interrupt.

## Interrupt
Persist intent, call exact turn/interrupt, wait/reconcile terminal state. Lost response/process fault -> TURN_UNKNOWN; pressing Telegram button alone never means cancellation succeeded.

## Delete
Two-stage intent+confirmation blocks new turns. If running, interrupt/reconcile first. Then durable DELETING claim -> exact thread/delete in owning profile -> definitive success/reconciliation -> purge controller content/jobs/temp/delivery -> remove live binding -> bounded no-content tombstone -> NO_DIALOGUE. Ambiguous delete -> DELETE_UNKNOWN retains minimum exact reconciliation IDs and blocks new dialogue.

## Account change
No context migration. To use another profile: finish/interrupt -> hard delete -> select new profile -> next prompt creates new dialogue.

## Model/reasoning change
Allowed NO_DIALOGUE or IDLE only, applies to next turn, runtime-validated. Running turn remains on captured selection.

## Controller restart
Routing returns SLEEP. Durable dialogue/job reloads; app-server is not assumed alive. Idle dialogue resumes lazily under same profile. In-flight/ambiguous job is reconciled before any new work. No prompt replay because process restarted.

## Telegram history
Hard delete does not automatically delete Telegram chat history; it is a separate surface outside V1.
