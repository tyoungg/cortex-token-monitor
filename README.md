# cortex-token-monitor

A Streamlit dashboard for monitoring Snowflake Cortex AI token usage.

## Data Sources

The dashboard queries token and credit usage from `TOKEN.USAGE.CORTEX_TOKEN_USAGE_V`. If the `TOKEN` application view is unavailable (for example, if app access is suspended or inactive), the app automatically falls back to querying Snowflake's standard `SNOWFLAKE.ACCOUNT_USAGE.CORTEX_FUNCTIONS_USAGE_HISTORY` view. If neither view is accessible (for example, if the account or organization is inactive), the app applies a third-level fallback that idles quietly with an informative notice and does not attempt any further actions or raise errors.

## Privacy

The **Per user** and **Leaderboard** views partially mask usernames that look like email addresses. The first two and last two characters of each email component are shown where possible, with the middle replaced by asterisks. For example, `johndoe@example.com` appears as `jo***oe@ex***le.c*m`. Short components are masked while retaining at most their first and last character. Non-email usernames and the `(unattributed)` label are shown as provided by Snowflake. Masking applies to display only; the app still uses the original usernames internally to keep users' usage separate.
