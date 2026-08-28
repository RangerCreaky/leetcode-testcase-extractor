# Leetcode Testcase Extractor

Leetcode's testcases are top secret – they are not public, and even premium users can't buy it. Why? It's what sets Leetcode apart from other platforms. If their testcase was public, anyone could easily copy them.

This project aims to get test cases by mimicing a human failing one test case at a time.

Using a selenium bot, I submit empty code, and leetcode tells me what testcase I got wrong. The bot adds an if statement to cover this testcase, and submits again. In doing so, it gains access to every test case.

## Current LeetCode UI

The extractor now targets LeetCode's current problem workspace:

- the Monaco code editor is selected through its `Code editor` accessibility label;
- language, reset, submit, and result controls use accessibility or `data-e2e-locator` hooks instead of layout-dependent element paths;
- submission completion and acceptance are read from the result panel rather than inferred from the URL; and
- the separate CodeMirror custom-testcase editor is deliberately ignored.

Install and run from the repository root:

```bash
python3 -m pip install -r requirements.txt
python3 main/runner.py 0
```

Pass multiple problem row numbers to process them sequentially. An accepted problem exits cleanly and the runner continues with the next requested row:

```bash
python3 main/runner.py 0 1 2
```

To process every unfinished row in `problem_data/problem_data.csv`:

```bash
python3 main/runner.py --all
```

The runner maintains a `Completed` column in that CSV. Missing values are initialized to `FALSE`; a row is changed to `TRUE` only after its submission is Accepted. Both `--all` and explicit row-number runs skip rows already marked `TRUE`, so an interrupted batch resumes from the first unfinished problem.

Cookie login remains supported through `main/leetcode_cookies.csv`. By default the extractor uses undetected-chromedriver in a visible Chrome window, because LeetCode's bot verification commonly blocks ordinary headless Selenium. Set `LEETCODE_HEADLESS=1` for server/container use, or `LEETCODE_DRIVER=selenium` to opt into the standard Selenium driver. Driver/browser versions are detected automatically; `CHROME_VERSION_MAIN` is available only as an override for unusual installations.

https://github.com/akhilkammila/leetcode-testcase-extractor/assets/68196076/f0a0e54b-d429-4d0e-b000-63d8aa63546f

https://github.com/akhilkammila/leetcode-testcase-extractor/assets/68196076/ac8f7def-3fe8-4957-a06b-b10ea8721cf1

# About
## Building the Bot
Leetcode makes it hard to access testcases. Leetcode only shows a testcase if a user fails on it – and it only shows one new testcase at a time.

To fail one test case at a time, I scrape the names of the input and output variables. After failing a testcase, I format an IF statement which passes just that test case, and resubmit.

Sometimes, leetcode doesn't even show the full testcase, because it is too long. I need to use the clipboard for this, clicking a copy button, and pasting it into a local file. There are also runtime errors when no if statement is caught, stale elements when submitting, etc.

The extractor waits 10 seconds before each submission and 20 seconds before retrying a rate-limited submission. These can be adjusted with `LEETCODE_SUBMIT_DELAY` and `LEETCODE_RETRY_DELAY`, respectively.

Full testcase values remain in the local `data/` archive. When large array, string, tuple, or dictionary literals would push submitted code toward LeetCode's source-size limit, the browser submission automatically uses stable SHA-256 comparisons instead. This keeps the local extraction lossless while making the judge submission much smaller.

Once I got the bot to deal with submission delays, login recaptchas, and runtime errors, it ran consistently.

## Scaling
Leetcode has a lot of problems, and a lot of testcases.

To be precise, there are 2700 problems, and most have 100 to 1000 testcases. Each testcase takes about 10 seconds, which equations to 3,750 hours (150+ days) of computing time.

This obviously is not feasible, so I needed to use multiprocessing. I built an alpine linux docker container capable of running the bot on any given problem. I then deployed the application to multiple EC2 C5.medium instances, and created a bash script to sequentially deploy docker containers for different problems. Each instance ran 2 simultaneous processes, and I spun up 5 instances.

<img width="720" alt="EC2Bash" src="https://github.com/akhilkammila/leetcode-testcase-extractor/assets/68196076/2dd953ed-6b03-4822-88d7-e61d8c8e587c">

<img width="592" alt="RunningOnEc2" src="https://github.com/akhilkammila/leetcode-testcase-extractor/assets/68196076/5e6d32bf-6e98-44dd-8f0c-3c46c08b7577">

## Results
The EC2 instances are able to solve nearly any problem on command. I ended up running them on 50 problems.

Some problems are completely solvable, like these:
#### [38. Count and Say](https://github.com/akhilkammila/leetcode-testcase-extractor/blob/main/data/38.%20Count%20and%20Say)
#### [22. Generate Parenthesis](https://github.com/akhilkammila/leetcode-testcase-extractor/blob/main/data/22.%20Generate%20Parentheses)

While for others, we can get as many testcases as we can, before we hit a 100,000 character limit:
#### [3. Longest Substring Without Repeating Characters](https://github.com/akhilkammila/leetcode-testcase-extractor/blob/main/data/3.%20Longest%20Substring%20Without%20Repeating%20Characters)
#### [1. Two Sum](https://github.com/akhilkammila/leetcode-testcase-extractor/blob/main/data/1.%20Two%20Sum)

The goal was to find the testcases for all premium problems. Unfortunately, the premium account gets shadow banned from submitting after a few hundred failed submissions in a row. For this reason, we can't solve a significant number of problems in a row.

## Reflection
This is the largest project I've taken on.

Remembering some of the hurdles I overcame:

    - Page loading errors: stale elements
        - elements constantly went stale, and elemnets on the screen were duplicated in the html
        - built robust base classes which waited for every element to appear
        - built helper methods to test for things like the number of lines in the editor

    - Parsing files
        - had to parse files to find out how to structure the if statements
        - if statements changed based on variable types

    - Submission errors
        - when code was submitted too soon, got an error
        - had to wait extra time and resubmit
        - network errors occasionally, for whenever internet cut out, of randomly
        - had to reload the page and try again

    - Large testcases were not fully shown
        - had to click the copy paste button, and then access the clipboard contents using pyperclip or tkinter

    - Login
        - selenium triggered captcha
        - tried using undetected chromebrowser, which worked
        - on docker, undetected chromedriver did not function, and the official docker image did not either
        - tried using captcha bot, and finally ended up using cookies to log in

    - Dockerizing
        - standalone chrome did not work
        - tried to get selenium running on a multitude of different platforms: alpine linux, debian, etc.
        - finally got it working on alpine linux

    - Copy paste
        - alpine linux does not have a clipboard
        - chromium clipboard blocks read/writes
        - ended up creating a new element on the page, doing keystrokes like CNTRL C + V, and then reading the element's value

    - Leetcode blocking too many submissions
        - after a few hundred consecutive submissions, leetcode blocks all submissions for multiple hours
        - waiting for more seconds between submissions does not stop this
        - fixed by using login credentials for different accounts

    - Network Errors for large files
        - leetcode does not accept files over 100,000 characters in length
        - can hash the input, but cannot hash the output to circumvent this
        - api calls within leetcode are blocked for security reasons
        - file compression can comrpess file by 50% at best – we need 100:1 or better
