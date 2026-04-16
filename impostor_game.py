import random
import sys
import pygame

# Screen configuration
WIDTH, HEIGHT = 960, 640
FPS = 60

# Entity configuration
PLAYER_SPEED = 260
NPC_SPEED = 130
PLAYER_RADIUS = 16
NPC_RADIUS = 13
NUM_NPCS = 6
KILL_DISTANCE = 46
PLAYER_KILL_COOLDOWN = 1.25
IMPOSTOR_KILL_INTERVAL_MIN = 5.0
IMPOSTOR_KILL_INTERVAL_MAX = 9.5
MAX_TENSION = 5

# Colors
BLUE = (56, 125, 255)
GREEN = (62, 205, 110)
DARK_BG = (24, 26, 33)
WHITE = (235, 238, 245)
YELLOW = (245, 214, 87)
RED = (232, 81, 72)
GRAY = (160, 170, 185)


class NPC:
    """Simple NPC with organic wandering and occasional direction changes."""

    def __init__(self, npc_id: int, x: float, y: float):
        self.id = npc_id
        self.x = x
        self.y = y
        self.alive = True
        self.direction = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
        if self.direction.length_squared() == 0:
            self.direction = pygame.Vector2(1, 0)
        self.direction = self.direction.normalize()
        self.change_timer = random.uniform(0.5, 1.8)

    def update(self, dt: float):
        if not self.alive:
            return

        self.change_timer -= dt
        if self.change_timer <= 0:
            # Blend current direction with a new random direction for smoother movement.
            new_dir = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
            if new_dir.length_squared() > 0:
                new_dir = new_dir.normalize()
                self.direction = (self.direction * 0.65 + new_dir * 0.35)
                if self.direction.length_squared() > 0:
                    self.direction = self.direction.normalize()
            self.change_timer = random.uniform(0.45, 1.7)

        self.x += self.direction.x * NPC_SPEED * dt
        self.y += self.direction.y * NPC_SPEED * dt

        # Bounce off boundaries to keep movement within screen.
        if self.x < NPC_RADIUS:
            self.x = NPC_RADIUS
            self.direction.x *= -1
        elif self.x > WIDTH - NPC_RADIUS:
            self.x = WIDTH - NPC_RADIUS
            self.direction.x *= -1

        if self.y < NPC_RADIUS:
            self.y = NPC_RADIUS
            self.direction.y *= -1
        elif self.y > HEIGHT - NPC_RADIUS:
            self.y = HEIGHT - NPC_RADIUS
            self.direction.y *= -1


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("2D Impostor Hunt")
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("arial", 22)
        self.big_font = pygame.font.SysFont("arial", 42, bold=True)

        self.player_pos = pygame.Vector2(WIDTH * 0.5, HEIGHT * 0.5)
        self.npcs = self._spawn_npcs(NUM_NPCS)
        self.impostor_id = random.choice(self.npcs).id

        self.status_message = "Find and eliminate the impostor."
        self.game_over = False
        self.player_won = False

        self.kills_total = 0
        self.innocents_killed = 0
        self.tension = 0

        self.last_player_kill_time = -999.0
        self.next_impostor_kill_time = random.uniform(
            IMPOSTOR_KILL_INTERVAL_MIN, IMPOSTOR_KILL_INTERVAL_MAX
        )
        self.elapsed_time = 0.0

    def _spawn_npcs(self, count: int):
        npcs = []
        for i in range(count):
            x = random.randint(NPC_RADIUS + 20, WIDTH - NPC_RADIUS - 20)
            y = random.randint(NPC_RADIUS + 20, HEIGHT - NPC_RADIUS - 20)
            npcs.append(NPC(i, x, y))
        return npcs

    def handle_input(self, dt: float):
        keys = pygame.key.get_pressed()
        move = pygame.Vector2(0, 0)

        if keys[pygame.K_w]:
            move.y -= 1
        if keys[pygame.K_s]:
            move.y += 1
        if keys[pygame.K_a]:
            move.x -= 1
        if keys[pygame.K_d]:
            move.x += 1

        if move.length_squared() > 0:
            move = move.normalize()
            self.player_pos += move * PLAYER_SPEED * dt

        # Keep player on-screen.
        self.player_pos.x = max(PLAYER_RADIUS, min(WIDTH - PLAYER_RADIUS, self.player_pos.x))
        self.player_pos.y = max(PLAYER_RADIUS, min(HEIGHT - PLAYER_RADIUS, self.player_pos.y))

    def alive_npcs(self):
        return [npc for npc in self.npcs if npc.alive]

    def nearest_alive_npc_in_range(self, max_distance: float):
        closest = None
        closest_dist_sq = max_distance * max_distance
        for npc in self.alive_npcs():
            dx = npc.x - self.player_pos.x
            dy = npc.y - self.player_pos.y
            dist_sq = dx * dx + dy * dy
            if dist_sq <= closest_dist_sq:
                closest = npc
                closest_dist_sq = dist_sq
        return closest

    def attempt_player_kill(self):
        if self.game_over:
            return

        if self.elapsed_time - self.last_player_kill_time < PLAYER_KILL_COOLDOWN:
            remain = PLAYER_KILL_COOLDOWN - (self.elapsed_time - self.last_player_kill_time)
            self.status_message = f"Kill cooldown: {remain:.1f}s"
            return

        target = self.nearest_alive_npc_in_range(KILL_DISTANCE)
        if not target:
            self.status_message = "No target in range."
            return

        target.alive = False
        self.kills_total += 1
        self.last_player_kill_time = self.elapsed_time

        if target.id == self.impostor_id:
            self.game_over = True
            self.player_won = True
            self.status_message = "You eliminated the impostor!"
        else:
            self.innocents_killed += 1
            self.tension += 2
            self.status_message = "You killed an innocent! Suspicion rises."
            if self.innocents_killed >= 2 or self.tension >= MAX_TENSION:
                self.game_over = True
                self.player_won = False
                self.status_message = "Too many innocents were killed. You lost."

    def call_vote(self):
        if self.game_over:
            return

        candidates = self.alive_npcs()
        if not candidates:
            self.game_over = True
            self.player_won = False
            self.status_message = "No one left to vote. The impostor escaped."
            return

        voted = random.choice(candidates)
        voted.alive = False

        if voted.id == self.impostor_id:
            self.game_over = True
            self.player_won = True
            self.status_message = "Vote succeeded! Impostor was ejected."
        else:
            self.tension += 1
            self.status_message = "Vote failed. An innocent was ejected."
            if self.tension >= MAX_TENSION:
                self.game_over = True
                self.player_won = False
                self.status_message = "Crew panic reached maximum. You lost."

    def impostor_action(self):
        if self.game_over:
            return

        # Impostor periodically eliminates another NPC.
        if self.elapsed_time < self.next_impostor_kill_time:
            return

        alive = self.alive_npcs()
        victims = [npc for npc in alive if npc.id != self.impostor_id]
        if victims:
            victim = random.choice(victims)
            victim.alive = False
            self.tension += 1
            self.status_message = "A body was found... tension increases."

        self.next_impostor_kill_time = self.elapsed_time + random.uniform(
            IMPOSTOR_KILL_INTERVAL_MIN, IMPOSTOR_KILL_INTERVAL_MAX
        )

        impostor_alive = any(n.alive and n.id == self.impostor_id for n in self.npcs)
        if not victims and impostor_alive:
            self.game_over = True
            self.player_won = False
            self.status_message = "Only the impostor remains. You lost."
        elif self.tension >= MAX_TENSION:
            self.game_over = True
            self.player_won = False
            self.status_message = "Chaos overwhelmed the crew. You lost."

    def update(self, dt: float):
        if self.game_over:
            return

        self.elapsed_time += dt
        self.handle_input(dt)

        for npc in self.npcs:
            npc.update(dt)

        self.impostor_action()

    def draw_hud(self):
        lines = [
            "WASD: Move | SPACE: Kill nearby | V: Call vote",
            f"Kills: {self.kills_total}   Innocents killed: {self.innocents_killed}",
            f"Tension: {self.tension}/{MAX_TENSION}",
            self.status_message,
        ]

        y = 10
        for i, text in enumerate(lines):
            color = WHITE if i < 3 else YELLOW
            surf = self.font.render(text, True, color)
            self.screen.blit(surf, (12, y))
            y += 26

    def draw_game_over(self):
        result = "YOU WIN" if self.player_won else "GAME OVER"
        color = YELLOW if self.player_won else RED
        text = self.big_font.render(result, True, color)
        sub = self.font.render("Press R to restart or ESC to quit", True, WHITE)

        self.screen.blit(
            text,
            (
                WIDTH // 2 - text.get_width() // 2,
                HEIGHT // 2 - text.get_height(),
            ),
        )
        self.screen.blit(
            sub,
            (
                WIDTH // 2 - sub.get_width() // 2,
                HEIGHT // 2 + 16,
            ),
        )

    def render(self):
        self.screen.fill(DARK_BG)

        pygame.draw.circle(
            self.screen,
            BLUE,
            (int(self.player_pos.x), int(self.player_pos.y)),
            PLAYER_RADIUS,
        )

        for npc in self.npcs:
            if npc.alive:
                pygame.draw.circle(self.screen, GREEN, (int(npc.x), int(npc.y)), NPC_RADIUS)
            else:
                pygame.draw.circle(self.screen, GRAY, (int(npc.x), int(npc.y)), NPC_RADIUS - 2)

        self.draw_hud()
        if self.game_over:
            self.draw_game_over()

        pygame.display.flip()

    def reset(self):
        self.__init__()

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        self.attempt_player_kill()
                    elif event.key == pygame.K_v:
                        self.call_vote()
                    elif event.key == pygame.K_r and self.game_over:
                        self.reset()

            self.update(dt)
            self.render()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
