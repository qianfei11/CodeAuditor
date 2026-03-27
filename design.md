I'm building a multi-stage code auditing Agent application using ClaudeCode SDK. Given a project with source code, it works like this:

Stage 1:
we split the project into modules based on their functionalities.
each module should be splitted into the granularity of files, i.e. each module should contain one or multiple files.
to achieve this, we need to understand the design and goal of the project, e.g. is it an implementation of a specific network protocol, say, HTTP?

in this stage we output one single markdown file containing two sections.
the first section is a high-level description of the functionality of the project.
the second section is a table, describing the functional module partition result.
the markdow file must have specific format, with verification code



Stage 2:
in this stage we assess the code base scale of one module, and check if we need to devide it into finer granularity analysis unit depending on the code base size of the module.
we assign each module divided by stage 1 to one sub-agent.
in next stage we will assign each analysis unit into one sub-agent for code auditing, so the code size of one analysis unit should be able to be hold into one sub-agent's context window for effecient code analyzing.
each analysis unit should be self-contained in this code logic, that one sug-agent has no need to reference or go deep into other code pathes to perform code auditing analysis on it.
basically, one analysis unit contains one or multiple files.
if a module is encapsulated into one file that is very large (thousands of lines), you can split the one single file into multiple analysis unit by giving function names
each analysis unit should be written into one markdown file, with specific format, with verification code.
the content of this stage's output will be used to build prompt for the next stage's sub-agent.



Stage 3:
in this stage we analyze each analysis unit defined in stage 2, looking for bugs and flaws in the code path.
one analysis unit from stage 2 is assigned to one sub-agent in this stage.
write findings as markdown files on disk, it must include the following fields:
- location: file, line number
- impact: the security impact of trigging the issue, e.g. UAF, double-free, etc.
- pre-requists: what specific run-time configuration or compile-time flag is required
- root cause analysis: analyze the root cause of this issue by commenting related code snippets, include separate analysis paragraphes if requried



Stage 4:
in this stage we identify the threat model and policy of this project.
search for the security anoucement in the project, especially files like SECURITY.md and VULNERABILITY.md in the project source tree.
search the git commit history (if any) for security fixes in the past,
visit the official website of the project,
search the internet,
to search for security anoucement, threat model, vulnerability assessment guidance, recently reported vulnerabilities, and all other information useful for assessing the severity of our findings.
write the findings into a markdown file, and finaly generate a conclusion about: which bugs and flaws should be considered a security vulnerability, and guidance to assess the severity of vulnerabilities for this project.
the guidance should be actionable.
use the common knowledge of a security researcher to identify vulnerabilities out of bugs, and the guidance is used as a reference and complementaty.
this guidance will be used as the prompt for the next stage to assess the bugs and flaws



Stage 5:
for each issue identified in stage 3, assign a sub-agent to:
1. verify the existance of the issue, go for the next steps if it is not a false-positive
2. check if the issue should be considered a security vulnerability, ignore those that are only "bugs" that can hardly introduce security impact
3. assess the severity of the vulnerability

each verified and assessed vulnerability be written into one markdown file


Stage 6:
write a final report capturing all the findings