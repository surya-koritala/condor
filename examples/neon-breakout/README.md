# Neon Breakout, written by Qwen3.8-Flash-Next on Glyd

![Neon Breakout playing itself](../../docs/media/neon-breakout.gif)

A complete arcade game in one HTML file (587 lines, no libraries), written by Qwen3.8-Flash-Next running on Glyd (Hummingbird level, fast mode) on one
RTX 4080 SUPER 16 GB (temperature 0.6, top-p 0.95). [index.html](index.html) is the model's last reply, unedited.

Open `index.html` in a browser to play (mouse or arrow keys, Space to launch and fire lasers, P to pause), or `index.html#autoplay` to
watch it play itself. It has five level layouts, 2- and 3-hit bricks, steel bricks, five power-ups (multi-ball, wide paddle, slow motion,
lasers, extra life), combos, particles, screen shake, Web Audio sound effects and a best score.

## How it was made

One request, then seven rounds of fixes, as a person would do it: run the game in Chrome, describe what is wrong, send the reply back.
Each round sent the original request, the model's latest file and the new message (fixes 2 and 6: the whole thread). Rounds 2, 5 and 6 include what we saw in Chrome
(a logged ball speed, an assignment that cancels autoplay, the line of a console error).

| Round | Wrote | Time |
|---|---:|---:|
| request | 12,500 tokens | 65.5 s |
| fix 1 | 12,624 tokens | 62.8 s |
| fix 2 | 12,423 tokens | 57.1 s |
| fix 3 | 12,802 tokens | 57.4 s |
| fix 4 | 13,014 tokens | 57.7 s |
| fix 5 | 13,139 tokens | 57.9 s |
| fix 6 | 13,193 tokens | 58.1 s |
| fix 7 | 13,779 tokens | 62.6 s |

About 103,500 tokens in 8 minutes of generation in all, at 190–260 tokens a second.

### The request

```text
Build a complete, polished arcade game as ONE self-contained HTML file (inline CSS and JavaScript only: no libraries, fonts, images or network requests). The game: "Neon Breakout".

Gameplay
- A paddle, a ball and a wall of glowing bricks on a full-window canvas with a dark starfield background.
- 5 levels with different brick layouts (rows, a pyramid, a checkerboard, a diamond, a fortress). Some bricks take 2 or 3 hits and change color as they crack; a few are unbreakable steel.
- Power-ups fall from broken bricks (about 1 in 8) and are caught with the paddle: Multi-ball (splits into 3 balls), Wide paddle (15 s), Slow motion (10 s), Laser paddle (fires with Space or click, 10 s), and Extra life. Each has its own color and letter.
- Score with a combo multiplier for consecutive bricks without touching the paddle; 3 lives; the ball speeds up gradually.
- The ball's angle depends on where it hits the paddle.

Screens and feel
- Title screen with the game name and "Press Space to start", while an autoplay demo plays behind it (the paddle tracks the ball well, so the demo looks good).
- Pause with P; game over screen with the final score, the best score (kept in localStorage) and "Press Space to play again"; a "Level cleared" banner between levels.
- Particle explosions in the brick's color, a short screen shake on hits, glowing trails behind the ball, and floating "+score" text.
- Sound effects made with the Web Audio API (paddle hit, brick break, power-up, life lost), started on the first key press or click.
- Controls: mouse, or the Left/Right arrow keys (or A/D); Space launches the ball or fires.

Code quality
- Size the canvas from the window on load and on resize, scaled by devicePixelRatio, and only then lay out the paddle and bricks; keep every position relative to the canvas size.
- One requestAnimationFrame loop with delta time (clamped), separate update and draw steps, and no errors in the console.

Reply with only the HTML in one ```html code block.
```

### Fix 1

```text
I tested it in Chrome. It looks great, but two bugs make it unplayable:

1. On the title screen the demo never moves: the ball sits on the paddle forever. In demo mode, serve the ball automatically half a second after it is placed, and again after every lost ball, so the demo keeps playing behind the title.
2. After Space starts the game and Space launches the ball, the ball disappears at once: it is not drawn, no bricks break, and no life is lost. Make sure a launched ball moves (pixels per second, scaled with the playfield), bounces off the walls, the paddle and the bricks, and is drawn every frame.

Walk through the whole flow in your head before answering: title demo, start, launch, break bricks, catch power-ups, lose a life, level cleared, game over, play again. Reply with the complete corrected file in one ```html code block.
```

### Fix 2

```text
Closer, but the ball still vanishes. I logged the state: on a 680 px tall field the served ball has speed 4352 px/s (speedFH = 6.4 field-heights per second), so it leaves the screen in one frame, a life is lost, and it resets onto the paddle. A good Breakout ball crosses the field in about 1.5 seconds: about 0.65 field-heights per second at level 1, rising slowly to at most 1.3. Check every other speed (power-ups, lasers, particles, paddle keys) for the same unit mistake, keep the substeps so the ball never skips through a brick or the paddle, and reply with the complete corrected file in one ```html code block.
```

### Fix 3

```text
It plays now. Polish before we ship it:
1. The title screen text sits on top of the bricks and is hard to read. Draw the title on a dark translucent rounded panel centered in the lower half of the field (below the bricks), and make the controls line readable (light gray, larger).
2. Level 1 is only teal and orange. Give each row its own neon color (red, orange, yellow, green, cyan, blue, purple, pink) and include a few 2-hit and 3-hit bricks from level 1, drawn with visible cracks.
3. Make the demo exciting to watch: the demo paddle should aim the ball at the area with the most bricks, and power-ups should drop more often in demo mode (1 in 4) and be caught, so viewers see multi-ball, lasers and the wide paddle.
4. Show the active power-ups with their remaining seconds under the score.
Reply with the complete file in one ```html code block.
```

### Fix 4

```text
Much better. Last fixes:
1. The top-left HUD overlaps: the power-up timers, their bars and the combo text are drawn on top of each other and over the lives. Lay them out as separate lines with fixed spacing under the score: lives, then combo, then one line per active power-up.
2. The rows still use only teal, orange and pink. Color bricks by row: row 0 #ff3b6b, 1 #ff8c4a, 2 #ffd23c, 3 #7dff6b, 4 #38e6c8, 5 #3c86ff, 6 #a46bff, 7 #ff6bd6; multi-hit bricks keep their row color with cracks drawn on them.
3. The demo paddle drifts to the left wall and the ball keeps hitting the left side. The demo should keep the ball under the paddle's surface (never miss) and pick the offset on the paddle that sends the ball toward the column with the most bricks left, across the whole width.
4. Add an autoplay mode: when the page URL ends with #autoplay, skip the title panel and play a real game (levels, score, power-ups, lasers firing automatically) with the demo controller, restarting after game over.
Reply with the complete file in one ```html code block.
```

### Fix 5

```text
Colors and HUD look right. One bug: with #autoplay the ball never serves and nothing moves. The boot code sets demoMode=true and then calls newGame(), which sets demoMode=false; clearLevel() also sets demoMode=false, so autoplay would stop after level 1 too. Keep the demo controller on for the whole autoplay session (every level and every restart after game over), and make sure lasers fire automatically while the laser power-up is active. Also, no 2-hit or 3-hit bricks show up on level 1: add a few. Reply with the complete file in one ```html code block.
```

### Fix 6

```text
Chrome throws "TypeError: Assignment to constant variable. at demoAim (line 291)". In demoAim's aim simulation, `const vx=Math.sin(a),vy=-Math.cos(a);` is declared const and then reflected off the walls (vx=Math.abs(vx) ...). Fix that, check the rest of the file for the same mistake, and reply with the complete file in one ```html code block.
```

### Fix 7

```text
It runs with no errors and lasers and multi-ball look great. The demo controller is still wrong: the paddle parks at the far left wall, and after a while the ball bounces straight up and down along the left edge forever (score stuck). Replace demoAim with a simple, robust controller:
- Predict where the lowest falling ball will reach the paddle's height (simulate the wall bounces), and move the paddle so the ball lands on it, at an offset of up to ±35% of the paddle's half-width chosen to send the ball toward the half of the field with more bricks left.
- When no ball is falling, drift the paddle back toward the field's center.
- Move at a capped speed so it looks human.
Also, for every ball: if |vx| falls below 15% of its speed, nudge the angle so it can never get stuck in a vertical or horizontal loop.
Reply with the complete file in one ```html code block.
```
