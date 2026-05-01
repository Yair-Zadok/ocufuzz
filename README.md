This is ocufuzz, an agentic fuzzer for frontend QA. 

It fuzzes a website with agentic agents running exploratory test sequences guided by summaries of previous runs. 

First, the agents explores and test the website -> reports any QA issues they find -> a summary report of all test sequences is generated.

https://github.com/user-attachments/assets/e8862b9e-6d3d-4f73-b10b-ab6ae412a492

See [HOWTORUN.md](HOWTORUN.md) for setup.

## Sample Reports

See [sample_runs](sample_runs) for example fuzzing reports. PDF versions of the reports are listed there for easy viewing on GitHub.

- In the [obvious issue site report](sample_runs/obvious-issue-site/report_converted_from_HTML.pdf), agents report many issues, including incorrect items being added to the shopping cart.
- In the [obscure issue site report](sample_runs/obscure-issue-site/report.html), agents find that the distance filter does not apply to the candidate dogs.

These are examples of semantic errors that agents are uniquely capable of finding.

AI notice:
AI agents have and are used to build this project

The targets of this project for Human/Agents are as follows:
- Understandable, simple code which allows for human review of every line with mental ease.
- Modular software design, i.e. standalone tools for agents to click on objects in the screen, DRY code, use helper functions to keep code clean, etc.
- Use existing libraries / codebases for tools or other needed functions where possible.
- Minimize lines of code within reason by using frameworks/libraries to where it makes sense.
- ALWAYS maintain a HOWTORUN.md which is constantly updated with SHORT instructions on how to run the project.

