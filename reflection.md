# PawPal+ Project Reflection

## 📸 Demo

<a href="/course_images/ai110/pawpal_screenshot_1.png" target="_blank"><img src='/course_images/ai110/pawpal_screenshot_1.png' title='PawPal App — Owner Info & Add a Pet' width='' alt='PawPal App' class='center-block' /></a>

<a href="/course_images/ai110/pawpal_screenshot_2.png" target="_blank"><img src='/course_images/ai110/pawpal_screenshot_2.png' title='PawPal App — Add a Task & Generate Schedule' width='' alt='PawPal App' class='center-block' /></a>

## 1. System Design
Enter owner + pet info
Add/edit care tasks
Generate a daily schedule
**a. Initial design**

- Briefly describe your initial UML design.
The diagram modeled five classes connected by ownership and usage relationships.

Owner sits at the top — it holds a preference string and available_minutes, and owns one or more Pet objects. Pet owns zero or more Task objects, since tasks are specific to a pet's care needs.

Task is a pure data object: a title, duration, priority, category, and completion flag.

Scheduler uses an Owner (and reaches pets/tasks through it) to produce a Schedule. The Schedule references, but does not own, a subset of tasks chosen to fit within the owner's time constraint.

- What classes did you include, and what responsibilities did you assign to each?
Task
The smallest unit of work in the system. Holds everything needed to describe a single care activity — what it is, how long it takes, how urgent it is, and whether it's been done. It makes no decisions; it just represents data.

Pet
Represents the animal being cared for. Owns a list of Tasks, since tasks are specific to a pet's needs. Knows basic facts about itself (species, age, notes) that could influence scheduling decisions down the line.

Owner
Represents the person using the app. Holds the time constraint (available_minutes) and preference (morning vs evening) that the scheduler must respect. Also holds a list of Pets, making it the top-level entry point into the system.

Schedule
The output of the system. An ordered list of tasks chosen for a specific day, along with the total time they consume and a plain-language explanation of why they were selected. It does not decide — it just holds and presents the result.

Scheduler
The only class with real logic. Takes an Owner and a list of Tasks, filters and sorts them by priority, and packs them into a Schedule that fits within the owner's available time. Also generates a human-readable explanation of its decisions.


**b. Design changes**

- Did your design change during implementation?
Yes
- If yes, describe at least one change and why you made it.
1. preferences: dict → preference: str

The original design used an open-ended dict for owner preferences. During review it became clear that the app only needs one preference — morning vs evening — so a plain str was sufficient. A dict would have added unnecessary flexibility with no concrete use case yet.

2. Scheduler dropped its pet attribute

The original UML had Scheduler holding both an owner and a pet as separate attributes. During review, this was redundant — Owner already holds a list of Pets, so pet was reachable through owner. Keeping both created a risk of them pointing to unrelated objects. Removing pet from Scheduler simplified the relationship and made Owner the single entry point.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
Couldn't delete of remove taskes when I wanted toto
- How did you decide which constraints mattered most?
I was just thinking about the fact that, what is the user made a mistake and would want to delete a task and that wasnt added to my application yet

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
Exact start-time matching instead of overlap detection The scheduler's conflict detector (pawpal_system.py:291) only flags two tasks as a collision when their scheduled_time strings are identical (e.g. both "09:00"). It does not check whether a task's duration causes it to run into the next task's start time. A 30-minute walk starting at 09:00 and a feeding starting at 09:15 would overlap from 09:15–09:30, but the scheduler raises no warning.
- Why is that tradeoff reasonable for this scenario?
Pet care tasks are rarely scheduled with surgical precision. An owner who writes down "09:00 — walk" and "09:30 — breakfast" is expressing intention, not a rigid timetable — the walk might run 18 minutes or 35 minutes depending on the dog. Treating scheduled_time as a hard interval boundary and flagging every case where start + duration > next_start would produce constant false-positive warnings for a household routine that is naturally flexible.

The exact-match check catches the one mistake that genuinely cannot be resolved at runtime: two tasks literally pinned to the same start time, where there is no ambiguity and no flexibility — the owner physically cannot do both simultaneously. That is the collision worth surfacing.

Overlap detection makes sense when tasks have fixed, non-negotiable durations (surgery slots, medication drips, transport windows). For a home pet-care schedule, exact-match gives useful signal without introducing noise that would train the owner to ignore all warnings.
---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
I asked Claude AI to compare the initial UML prose against the final code and identify gaps
Test generation: used AI to draft happy-path and edge-case tests, then ran them to verify
Debugging: when test_edge_complete_task_twice failed, AI diagnosed that complete_task searches by title and finds the pending recurring copy — not the original
- What kinds of prompts or questions were most helpful?
#codebase + a specific question (e.g. "what edge cases should I test?")
Asking AI to explain why a test failed before accepting any fix

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
The double-completion test — AI's first version asserted the second call was a no-op.

- How did you evaluate or verify what the AI suggested?
The test failed, revealing a real bug. Rather than silently fixing the test to pass, you kept it and updated it to document the actual (surprising) behaviour. That's a moment where you evaluated the AI's assumption and rejected it.


---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
Sorting correctness, recurrence logic, conflict detection, happy paths, edge cases — 76 tests total in tests/test_pawpal.py

- Why were these tests important?
Recurrence and conflict detection have subtle boundary conditions (exactly 7 days, same-title task matching) that are invisible without tests

**b. Confidence**

- How confident are you that your scheduler works correctly?
4/5
- What edge cases would you test next if you had more time?
Edge cases to test next: overlap detection (30-min task at 09:00 + task at 09:15), multi-pet budget priority, UI-layer guard against double-completion
---

## 5. Reflection

**a. What went well**
- What part of this project are you most satisfied with?
The test coverage and scheduling logic. Writing 76 tests forced me to think precisely about edge cases I would have glossed over — the recurring task matching, the 7-day boundary for is_due_today, and the exact-match conflict detector all emerged more clearly from testing than from design alone.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
I'd add true overlap detection to the conflict checker — right now it only flags two tasks at the exact same start time, but a 30-minute walk at 09:00 and a feeding at 09:15 silently overlap. I'd also redesign the task removal workflow; during development I found it frustrating that deleting a task wasn't available earlier in the UI, which meant recovering from mistakes required workarounds.


**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
AI suggestions need to be run, not just read. When AI drafted the double-completion test, its assertion looked reasonable on paper — but running it exposed a real bug in how complete_task matches by title. That moment taught me to treat AI output as a first draft that the test suite has to approve, not a finished answer.

