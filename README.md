# cortex-token-monitor

A Streamlit dashboard for monitoring Snowflake Cortex AI token usage.

## Privacy

The **Per user** and **Leaderboard** views mask usernames that look like email addresses. Each distinct email-style username is shown as a numbered label (for example, `Email user 1`) instead of the original address. Non-email usernames and the `(unattributed)` label are shown as provided by Snowflake. The masking is for display in the app; the Snowflake query still reads the original `user_name` values.
