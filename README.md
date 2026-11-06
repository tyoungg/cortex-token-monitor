# cortex-token-monitor

A Streamlit dashboard for monitoring Snowflake Cortex AI token usage.

## Privacy

The **Per user** and **Leaderboard** views partially mask usernames that look like email addresses. The first two and last two characters of each email component are shown where possible, with the middle replaced by asterisks. For example, `johndoe@example.com` appears as `jo***oe@ex***le.c*m`. Short components are masked while retaining at most their first and last character. Non-email usernames and the `(unattributed)` label are shown as provided by Snowflake. Masking applies to display only; the app still uses the original usernames internally to keep users' usage separate.
