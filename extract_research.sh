#!/bin/bash
# Extract research content from agent output files and write to RESEARCH.md

TASK_DIR="/tmp/claude/-Users-dustycyanide-Documents-projects-ai-vibefaster-django-react-shipfast/tasks"
SPECS_DIR="/Users/dustycyanide/Documents/projects/ai/vibefaster/django_react_shipfast/lichess_specs"

extract_content() {
    local input_file="$1"
    local output_file="$2"
    local temp_file=$(mktemp)

    # Method 1: Try markdown code block
    awk '
        /^```markdown/ { capture=1; next }
        /^```$/ && capture { capture=0; exit }
        capture { print }
    ' "$input_file" > "$temp_file"

    if [ -s "$temp_file" ]; then
        mv "$temp_file" "$output_file"
        return 0
    fi

    # Method 2: Try heredoc format (cat > file << 'ENDOFFILE' ... ENDOFFILE)
    # Extract content between ENDOFFILE markers
    awk '
        /ENDOFFILE$/ && !started { started=1; next }
        /^ENDOFFILE/ && started { exit }
        started { print }
    ' "$input_file" > "$temp_file"

    if [ -s "$temp_file" ]; then
        mv "$temp_file" "$output_file"
        return 0
    fi

    # Method 3: Look for "# Lichess" or "# Research" header and extract from there
    awk '
        /^# Lichess|^# .*Research/ { capture=1 }
        /^---$/ && capture && found_content {
            # Keep going after first ---
            found_content++
        }
        capture {
            print
            found_content=1
        }
    ' "$input_file" > "$temp_file"

    if [ -s "$temp_file" ]; then
        mv "$temp_file" "$output_file"
        return 0
    fi

    rm -f "$temp_file"
    return 1
}

process_agent() {
    local agent_id="$1"
    local dir="$2"

    input_file="$TASK_DIR/${agent_id}.output"
    output_file="$SPECS_DIR/$dir/RESEARCH.md"

    echo "Processing $dir (agent $agent_id)..."

    if [ ! -f "$input_file" ]; then
        echo "  ✗ Output file not found"
        return 1
    fi

    if extract_content "$input_file" "$output_file"; then
        lines=$(wc -l < "$output_file" | tr -d ' ')
        echo "  ✓ Wrote $lines lines"
        return 0
    else
        echo "  ✗ No content extracted"
        return 1
    fi
}

echo "Extracting research documents..."
echo ""

success=0
failed=0

process_agent "abe0275" "00-overview" && ((success++)) || ((failed++))
process_agent "adb27fa" "01-architecture" && ((success++)) || ((failed++))
process_agent "a51a5e1" "02-core-features" && ((success++)) || ((failed++))
process_agent "a83be65" "03-game-modes" && ((success++)) || ((failed++))
process_agent "a8dd5e3" "04-training" && ((success++)) || ((failed++))
process_agent "a57d299" "05-competitive" && ((success++)) || ((failed++))
process_agent "ab89ebb" "06-social" && ((success++)) || ((failed++))
process_agent "ae742e0" "07-content" && ((success++)) || ((failed++))
process_agent "abd24aa" "08-api" && ((success++)) || ((failed++))
process_agent "afe8d1f" "09-resources" && ((success++)) || ((failed++))

echo ""
echo "Done: $success succeeded, $failed failed"
