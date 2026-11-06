# cortex-token-monitor

A Streamlit dashboard for monitoring Snowflake Cortex AI token usage.

## Privacy

The **Per user** and **Leaderboard** views partially mask usernames that look like email addresses. The first two and last two characters of the address's local part are shown, with the middle replaced by asterisks (for example, `johndoe@example.com` appears as `jo***oe@example.com`). The domain remains visible. Non-email usernames and the `(unattributed)` label are shown as provided by Snowflake. Masking applies to display only; the app still uses the original usernames internally to keep users' usage separate.
