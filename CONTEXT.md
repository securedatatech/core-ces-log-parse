# Cisco ESA Mail Log Extraction

This context covers selecting and correlating mail-processing activity from Cisco Email Security Appliance (ESA) logs. It names the address and message identifiers used to produce focused thread extracts.

## Language

### Correlation

**Matched address**:
An email address selected for extraction from a mail log. It is a correlation target, not a claim that the address is the message's sender or recipient.
_Avoid_: sender, sender email address, recipient (when referring to the extraction target)

**MID (Message ID)**:
The numeric identifier used to group log entries belonging to one mail-processing record.
_Avoid_: thread ID, queue ID

**Log entry**:
A single mail-processing record in an ESA log.
_Avoid_: event, log line (when naming the domain record)

**Address–MID association**:
A link between a matched address and a MID established when both appear in the same log entry.
_Avoid_: inferred correlation, cross-line match

**Thread extract**:
A focused output bundle containing a matched address, its associated MIDs, and log entries grouped under those MIDs. It traces mail processing and is not an email conversation.
_Avoid_: email thread, conversation
