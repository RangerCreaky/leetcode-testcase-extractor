class LoginPage:
    URL = "https://leetcode.com/accounts/login/"
    TITLE = "Account Login - LeetCode"
    LOADING_SCREEN_ID = "initial-loading"
    USERNAME_BTN_ID = "id_login"
    PASSWORD_BTN_ID = "id_password"
    SIGN_IN_BUTTON_ID = "signin_btn"

class ProblemPage:
    URL =  "https://leetcode.com/problemset/all/"
    TITLE = "Problems - LeetCode"
    LINK_TO_PROBLEM_CSS = "a[href^='/problems/']"

class SingleProblemPage:
    # The main code editor is Monaco.  LeetCode also renders a CodeMirror
    # editor for custom testcases, so generic `.cm-*` selectors target the
    # wrong editor in the current UI.
    EDITOR_CSS = "textarea[aria-label='Code editor']"
    EDITOR_LINES_CSS = ".monaco-editor .view-lines .view-line"

    LANGUAGE_BTN_XPATH = (
        "//button[@aria-haspopup='dialog' and normalize-space(.) != 'Auto' "
        "and .//*[contains(@class, 'fa-chevron-down')]]"
    )
    PYTHON_OPTION_XPATH = (
        "//*[@role='dialog']//*[normalize-space()='Python3']"
        "/ancestor::div[contains(@class, 'cursor-pointer')][1]"
    )
    SUBMIT_BUTTON_CSS = "button[data-e2e-locator='console-submit-button']"
    SUBMIT_BUTTON_FALLBACK_CSS = (
        "button[data-e2e-locator='console-submit-button'], "
        "button[data-e2e-locator='submit-button']"
    )
    # The Testcase tab at the bottom of the editor; clicking it expands the
    # console panel when it is collapsed so the submit button becomes visible.
    CONSOLE_TAB_CSS = "[data-e2e-locator='console-testcase-tab']"
    RESET_BUTTON_XPATH = "//button[.//*[contains(@class, 'fa-arrow-rotate-left')]]"
    RESET_CONFIRM_XPATH = "//*[@role='dialog']//button[normalize-space()='Confirm']"

    DEFAULT_SUBMISSION = "return"

class ResultConsole:
    # Submissions can render in either the bottom console or the full
    # "All Submissions" detail tab.  The latter uses a status heading and
    # does not include data-e2e-locator="console-result".
    STATUS_CSS = (
        "[data-e2e-locator='console-result'], "
        "[data-e2e-locator='submission-result'], "
        "h3"
    )
    TERMINAL_STATUSES = {
        "Accepted",
        "Wrong Answer",
        "Runtime Error",
        "Compile Error",
        "Time Limit Exceeded",
        "Memory Limit Exceeded",
        "Output Limit Exceeded",
        "Internal Error",
    }
    RETRYABLE_MESSAGES = (
        "You have attempted to run code too soon",
        "too frequently",
        "too soon",
        "network",
        "failed to submit",
        "something went wrong",
    )

    RESULT_PANEL_XPATH = (
        "./ancestor::div[.//*[normalize-space()='Input'] "
        "and .//*[normalize-space()='Expected']][1]"
    )

    @classmethod
    def canonical_status(cls, value):
        normalized = " ".join(value.split())
        for status in sorted(cls.TERMINAL_STATUSES, key=len, reverse=True):
            if normalized == status or normalized.startswith(status + " "):
                return status
        return ""
