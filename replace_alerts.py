#!/usr/bin/env python3
# Script to replace all alert() and confirm() with custom styled versions

import re

# Read the file
with open('templates/bot.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to find and replace alert() calls
# We need to handle both single and multi-line alerts
def replace_alerts(text):
    # Replace simple alert() calls
    # Match: alert('message') or alert("message") or alert(`message`)
    pattern = r"alert\((['\"`])((?:(?!\1).)*)\1\)"

    def alert_replacer(match):
        quote = match.group(1)
        message = match.group(2)

        # Determine type based on message content
        if '✅' in message or 'SUCCESS' in message.upper() or 'activated' in message.lower():
            alert_type = 'success'
        elif '❌' in message or 'ERROR' in message.upper() or 'Error' in message:
            alert_type = 'error'
        elif '⚠️' in message or 'WARNING' in message.upper() or 'INSUFFICIENT' in message:
            alert_type = 'warning'
        else:
            alert_type = 'info'

        return f"showCustomAlert({quote}{message}{quote}, '{alert_type}')"

    text = re.sub(pattern, alert_replacer, text, flags=re.DOTALL)

    # Handle multi-line alerts (concatenated strings)
    pattern_multiline = r"alert\((['\"`].*?['\"`](?:\s*\+\s*['\"`].*?['\"`])*)\)"

    def multiline_alert_replacer(match):
        full_message = match.group(1)

        # Determine type based on message content
        if '✅' in full_message or 'SUCCESS' in full_message.upper():
            alert_type = 'success'
        elif '❌' in full_message or 'ERROR' in full_message.upper():
            alert_type = 'error'
        elif '⚠️' in full_message or 'WARNING' in full_message.upper():
            alert_type = 'warning'
        else:
            alert_type = 'info'

        return f"await showCustomAlert({full_message}, '{alert_type}')"

    text = re.sub(pattern_multiline, multiline_alert_replacer, text, flags=re.DOTALL)

    return text

# Replace confirm() calls
def replace_confirms(text):
    # Match: confirm('message') or const x = confirm('message')
    # We need to make these async

    # Pattern for simple confirm assigned to a variable
    pattern = r"(const\s+\w+\s*=\s*)confirm\((['\"`])((?:(?!\2).)*)\2\)"

    def confirm_replacer(match):
        var_part = match.group(1)
        quote = match.group(2)
        message = match.group(3)

        # Determine type based on message content
        if 'DANGER' in message.upper() or '🚨' in message or 'FINAL' in message:
            confirm_type = 'danger'
        else:
            confirm_type = 'warning'

        return f"{var_part}await showCustomConfirm({quote}{message}{quote}, '{confirm_type}')"

    text = re.sub(pattern, confirm_replacer, text, flags=re.DOTALL)

    # Pattern for multi-line confirm
    pattern_multiline = r"(const\s+\w+\s*=\s*)confirm\(\s*(['\"`].*?['\"`](?:\s*\+\s*.*?)*)\s*\)"

    def multiline_confirm_replacer(match):
        var_part = match.group(1)
        full_message = match.group(2)

        # Determine type
        if 'DANGER' in full_message.upper() or '🚨' in full_message or 'FINAL' in full_message:
            confirm_type = 'danger'
        else:
            confirm_type = 'warning'

        return f"{var_part}await showCustomConfirm({full_message}, '{confirm_type}')"

    text = re.sub(pattern_multiline, multiline_confirm_replacer, text, flags=re.DOTALL)

    # Pattern for if (!confirm(...))
    pattern_if = r"if\s*\(\s*!confirm\((['\"`])((?:(?!\1).)*)\1\)\s*\)"

    def if_confirm_replacer(match):
        quote = match.group(1)
        message = match.group(2)
        return f"if (!await showCustomConfirm({quote}{message}{quote}, 'warning'))"

    text = re.sub(pattern_if, if_confirm_replacer, text, flags=re.DOTALL)

    # Pattern for if (confirm(...))
    pattern_if_pos = r"if\s*\(\s*confirm\((['\"`])((?:(?!\1).)*)\1\)\s*\)"

    def if_pos_confirm_replacer(match):
        quote = match.group(1)
        message = match.group(2)
        return f"if (await showCustomConfirm({quote}{message}{quote}, 'warning'))"

    text = re.sub(pattern_if_pos, if_pos_confirm_replacer, text, flags=re.DOTALL)

    return text

# Apply replacements
content = replace_alerts(content)
content = replace_confirms(content)

# Make affected functions async
# Find functions that now use await and make them async if not already
functions_to_make_async = [
    'startBot',
    'stopBot',
    'sellPosition',
    'upgradeBoost',
    'closePrivateKeyModal',
    'confirmRegenerateWallet',
    'regenerateWallet',
    'endSimulationMode',
    'openPaymentModal'
]

for func_name in functions_to_make_async:
    # Pattern to find function declaration
    pattern = f"(function {func_name}\\s*\\([^)]*\\))"
    replacement = f"async function {func_name}\\1"
    content = re.sub(f"function {func_name}\\s*\\(", f"async function {func_name}(", content)

# Write back
with open('templates/bot.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("All alert() and confirm() have been replaced with custom styled versions!")
print("Affected functions have been made async.")
