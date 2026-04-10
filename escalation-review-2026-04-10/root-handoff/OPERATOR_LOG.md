# OPERATOR LOG

Every human action that affects the experiment. The honest record of autonomous vs assisted.

## Intervention Log

| Timestamp | HB | Type | Description | Impact |
|-----------|-----|------|-------------|--------|
| — | 0 | SETUP | Initialized workspace, pre-granted Surge + analytics + GitHub | Baseline |

## Types
- **SETUP**: Initial config
- **TOOL_GRANT**: Approved MEDIUM/HIGH tool request
- **TOOL_DENY**: Denied tool request (reason)
- **REVIEWER_OVERRIDE**: Overrode AI reviewer decision (approve something it denied, or vice versa)
- **MANUAL_FIX**: Fixed something the agent broke
- **RESTART**: Re-ran a heartbeat
- **PAUSE**: Paused the experiment
- **CONFIG_CHANGE**: Changed OpenClaw config, model, or sandbox settings
- **OTHER**: Anything else

## Summary (fill at end of pilot)
- Total heartbeats: __ / 20
- Tool requests: __ received, __ granted, __ denied
- Outreach proposals: __ total, __ approved by reviewer, __ denied, __ operator overrides
- Manual fixes: __
- Restarts: __
- Total operator time: __
- Estimated API cost: $__
