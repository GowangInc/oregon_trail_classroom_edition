# Oregon Trail: Classroom Edition

A complete recreation of the classic *The Oregon Trail* rebuilt for the classroom. A teacher hosts a Python server and assigns students into 2–8 wagon parties (up to 4 students each). All parties travel the same trail simultaneously, experiencing the same weather and calendar, but each party controls its own pace, rations, and strategy.

## Quick Start

```bash
pip install -r requirements.txt
python server.py
```

- Teacher opens `http://localhost:5000/host`
- Students open `http://localhost:5000` and join the lobby

## Tech Stack

- **Backend**: Python 3.11+, Flask, Flask-SocketIO
- **Frontend**: Vanilla HTML5, CSS3, JavaScript (ES6 modules)
- **No build step required**

## Project Structure

```
server.py              # Flask-SocketIO server
session_manager.py     # Game loop, ticks, state management
party_engine.py        # Core game logic (pure Python)
models.py              # Data classes (Player, Party, Inventory, etc.)
game_data.py           # Constants, events, prices, landmarks

static/
  js/
    hunting_game.js    # 8-bit hunting mini-game engine
    hunting_sprites.js # Procedural pixel-art renderer
    hunting_terrain.js # Zone-based obstacle system
    hunting_palette.js # HSL color palette
    network.js         # Socket.IO client wrapper
    ui.js              # Frontend UI rendering
    main.js            # Client entry point
    host.js            # Host dashboard logic
  css/
    style.css          # Terminal-green aesthetic

templates/
  index.html           # Student client
  host.html            # Teacher dashboard
```

## Hunting Mini-Game

The project includes a faithful remake of the original 1985 Apple II / 1990 DOS hunting mini-game:

- **100 lb carry limit** with waste messaging
- **35-second daylight timer**
- **Third-person hunter** with 8-directional aiming
- **Projectile bullets** instead of instant-hit
- **Upside-down flip** death animation (iconic original behavior)
- **5 terrain zones** with zone-appropriate animals and obstacles
- **Procedural pixel-art sprites** using authentic Apple II 6-color palette

See [`oregon_trail_original_research.md`](oregon_trail_original_research.md) for primary-source research from the original lead designer.

## Documentation

| File | Description |
|------|-------------|
| [`project.md`](project.md) | Full project architecture and design spec |
| [`agent.md`](agent.md) | Coding standards and agent instructions |
| [`oregon_trail_reference.md`](oregon_trail_reference.md) | Game reference data and formulas |
| [`oregon_trail_original_research.md`](oregon_trail_original_research.md) | Primary-source research on the original game |
| [`hunting_minigame_assets_spec.md`](hunting_minigame_assets_spec.md) | Sprite dimensions and asset guidelines |
| [`hunting_canvas_architecture.md`](hunting_canvas_architecture.md) | Canvas animation architecture |

## License

Educational / Classroom use. Original *The Oregon Trail* is copyright MECC.
