# Haru Episode Builder

A Streamlit app for creating Task and Scenario JSON files for the Haru social robot.

---

## Features

- **Two-page workflow**: Task Builder and Scenario Builder
- **Template-based tasks**: Load from predefined templates with parameter substitution
- **Four action types**:
  - `HARU_CONVERSATE` - Dialogue with structured goals
  - `HARU_GAZE` - Gaze tracking (person/group)
  - `HARU_SHARE` - Display content on screen (video, image, or collected results)
  - `HARU_REQUEST` - Request input from users (avatars, drawings, photos, text)
- **Visual action flow**: Timeline view with parallel action support
- **Inline editing**: Edit goals, success criteria, timeout, and instructions directly in preview
- **Block insertion**: Insert actions before/after with content or goal mode
- **Scenario composition**: Combine multiple tasks into scenarios

---

## Setup

### Using Docker (recommended)

```bash
docker compose up --build
```

Open http://localhost:8501

### Using `uv`

```bash
uv venv
source .venv/bin/activate
uv sync
streamlit run app.py
```

### Using pip

```bash
python -m venv .venv
source .venv/bin/activate
pip install streamlit pydantic
streamlit run app.py
```

---

## Pages

### Task Builder

Create individual tasks from templates or load existing tasks.

1. **Load**: Select a template or load an existing task
2. **Configure**: Fill in template parameters (topic, video URL, etc.)
3. **Preview & Edit**: View action flow, edit goals/timeout/instructions, insert or delete actions
4. **Save**: Save to Scenario Builder or download JSON

#### Block Templates

Insert actions using predefined block templates, each with a **Content** or **Goal** mode:

| Block | Action Type | Description |
|-------|-------------|-------------|
| Conversate | CONVERSATE | TTS speech with voice genre and routine |
| Converse & Gaze | CONVERSATE + GAZE | Bonded speech and gaze (GROUP or GAZE_INDIVIDUAL) |
| Request iPads | REQUEST | Request avatars, drawings, photos, or text from iPads |
| Share Video | SHARE | Display video on projector with loop/mute/wait options |
| Share Image | SHARE | Display image on projector |
| Share Results | SHARE | Display collected results from a previous REQUEST |

### Scenario Builder

Combine saved tasks into scenarios.

1. **Add tasks** from the left panel
2. **Reorder** with up/down buttons
3. **Download** the complete scenario JSON

---

## Action Types

| Type | Icon | Description |
|------|------|-------------|
| CONVERSATE | 💬 | Dialogue with goals, success criteria, timeout |
| GAZE | 👁️ | Look at person (TRACK_PERSON) or group (GROUP) |
| SHARE | 🖥️ | Display video, image, text, or collected results |
| REQUEST | 📥 | Request avatar, drawing, photo, or text input |

---

## Templates

Templates are JSON files in `data/tasks/templates/` with optional parameter placeholders:

```json
{
  "template": {
    "parameters": {
      "video_url": {
        "description": "URL to the how-to video",
        "example": "/shared/projector/resources/video.webm"
      }
    }
  },
  "actions": [...]
}
```

Included templates:

| Template | Description |
|----------|-------------|
| Avatar | Request avatar creation + display on projector |
| Drawing | Request drawing + display on projector |
| Greet | Self-introduction and greeting |
| LearnAbout | Learn about a topic |
| AskAbout | Ask questions about a topic |
| DoYouPrefer | Preference gathering |
| WouldYouRather | Would you rather questions |
| AgreeDisagree | Opinion gathering |
| ShareAndRelate | Collaborative sharing |
| BuildTheIdea | Idea building |
| Prediction | Prediction task |
| RankIt | Ranking task |
| FacilitateDiscussion | Discussion facilitation |
| Sleep | Haru sleep behavior |
| Closing | Session closing |
| WelcomeBack | Welcome back |
| HaruShareIceCream | Haru shares ice cream preferences |

---

## Project Structure

```
simple-haru-episode-builder/
├── app.py                    # Main entry point
├── Dockerfile
├── docker-compose.yml
├── views/
│   ├── scenario_builder.py   # Scenario Builder page
│   └── task_builder.py       # Task Builder page + block templates
├── src/
│   ├── models/               # Pydantic data models
│   ├── components/           # UI components + action editors
│   ├── services/             # Template, validation, import/export
│   └── utils/                # Constants and helpers
└── data/
    └── tasks/
        ├── templates/        # Task templates (JSON)
        └── saved/            # Saved tasks
```
