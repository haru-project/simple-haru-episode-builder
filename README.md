# Haru Scenario Builder

A Streamlit app for creating Task and Scenario JSON files for the Haru social robot.

---

## Features

- **Two-page workflow**: Task Builder and Scenario Builder
- **Template-based tasks**: Load from predefined templates with parameter substitution
- **Four action types**:
  - `HARU_CONVERSATE` - Dialogue with structured goals
  - `HARU_GAZE` - Gaze tracking (person/group)
  - `HARU_SHARE` - Display content on screen
  - `HARU_REQUEST` - Request input from users
- **Visual action flow**: Timeline view with parallel action support
- **Inline editing**: Edit timeout and additional instructions directly in preview
- **Scenario composition**: Combine multiple tasks into scenarios

---

## Setup

### Using `uv` (recommended)

```bash
# Create virtual environment
uv venv

# Activate
source .venv/bin/activate

# Install dependencies
uv sync
```

### Using pip

```bash
python -m venv .venv
source .venv/bin/activate
pip install streamlit pydantic
```

---

## Run

```bash
streamlit run app.py
```

Open http://localhost:8501

---

## Pages

### Task Builder

Create individual tasks from templates or load existing tasks.

1. **Load**: Select a template or load an existing task
2. **Configure**: Fill in template parameters (topic, etc.)
3. **Preview & Edit**: View action flow, edit timeout and instructions
4. **Save**: Save to Scenario Builder or download JSON

### Scenario Builder

Combine saved tasks into scenarios.

1. **Add tasks** from the left panel
2. **Reorder** with up/down buttons
3. **Download** the complete scenario JSON

---

## Action Types

| Type | Icon | Description |
|------|------|-------------|
| CONVERSATE | `conversation` | Dialogue with goals, success criteria, timeout |
| GAZE | `eye` | Look at person or group |
| SHARE | `screen` | Display text, image, or video |
| REQUEST | `inbox` | Request avatar photo or text input |

---

## Project Structure

```
simple-haru-episode-builder/
├── app.py                    # Main entry point
├── views/
│   ├── scenario_builder.py   # Scenario Builder page
│   └── task_builder.py       # Task Builder page
├── src/
│   ├── models/               # Pydantic data models
│   ├── components/           # UI components
│   ├── services/             # Template service
│   └── utils/                # Constants and helpers
└── data/
    └── tasks/
        ├── templates/        # Task templates
        └── saved/            # Saved tasks
```

---

## Templates

Templates are JSON files with parameter placeholders:

```json
{
  "template": {
    "parameters": {
      "topic": {
        "description": "The topic to discuss",
        "example": "favorite movies"
      }
    }
  },
  "actions": [...]
}
```

Place templates in `data/tasks/templates/` or configure a custom path in `src/utils/constants.py`.
