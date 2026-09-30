from __future__ import annotations

import random

from snake_game.engine import AI_ID, GameEngine
from snake_game.models import Direction, GameConfig, SnakeState
from snake_game.strategies import (
    STRATEGY_REGISTRY,
    StrategiBFS,
    GreedyStrategy,
    MoveStrategy,
    SafeRandomStrategy,
    StrategiUCS,
    register_strategy,
)


def test_safe_random_always_selects_a_legal_move() -> None:
    game = GameEngine(GameConfig(rows=10, columns=10), rng=random.Random(1))
    game.snakes[AI_ID] = SnakeState(AI_ID, [(0, 0), (0, 1), (1, 1)], Direction.UP)
    game.apples = [(9, 9)]
    snapshot = game.snapshot()
    move = SafeRandomStrategy().choose_move(snapshot, AI_ID, random.Random(2))
    assert move in snapshot.legal_moves_for(AI_ID)


def test_greedy_reduces_apple_distance_when_possible() -> None:
    game = GameEngine(GameConfig(rows=10, columns=10), rng=random.Random(1))
    game.snakes[AI_ID] = SnakeState(AI_ID, [(3, 3), (2, 3), (1, 3)], Direction.RIGHT)
    game.apples = [(3, 0), (9, 9)]
    move = GreedyStrategy().choose_move(game.snapshot(), AI_ID, random.Random(2))
    assert move is Direction.UP


def test_trapped_strategies_fall_back_to_current_direction() -> None:
    game = GameEngine(GameConfig(rows=10, columns=10))
    game.snakes[AI_ID] = SnakeState(
        AI_ID,
        [(0, 0), (0, 1), (1, 1), (1, 0)],
        Direction.LEFT,
    )
    game.apples = [(8, 8)]
    snapshot = game.snapshot()
    assert snapshot.legal_moves_for(AI_ID) == ()
    assert SafeRandomStrategy().choose_move(snapshot, AI_ID, random.Random()) is Direction.LEFT
    assert GreedyStrategy().choose_move(snapshot, AI_ID, random.Random()) is Direction.LEFT


def test_registered_custom_strategy_appears_in_registry() -> None:
    @register_strategy("Test Strategy")
    class TestStrategy(MoveStrategy):
        def choose_move(self, snapshot, snake_id, rng):
            return Direction.UP

    assert STRATEGY_REGISTRY["Test Strategy"] is TestStrategy


def test_bfs_finds_shortest_path_to_nearest_apple() -> None:
    game = GameEngine(GameConfig(rows=10, columns=10), rng=random.Random(1))
    game.snakes[AI_ID] = SnakeState(AI_ID, [(3, 3), (2, 3), (1, 3)], Direction.RIGHT)
    game.apples = [(3, 0), (9, 9)]
    snapshot = game.snapshot()
    assert StrategiBFS.cari_jalur(snapshot, AI_ID) == [Direction.UP] * 3
    assert StrategiBFS().choose_move(snapshot, AI_ID, random.Random()) is Direction.UP


def test_bfs_routes_around_a_wall_of_body_segments() -> None:
    game = GameEngine(GameConfig(rows=10, columns=10), rng=random.Random(1))
    # A long vertical body blocks the direct route to the apple on the right.
    body = [(2, 5)] + [(3, y) for y in range(5, 0, -1)] + [(2, y) for y in range(1, 5)]
    game.snakes[AI_ID] = SnakeState(AI_ID, body, Direction.LEFT)
    game.apples = [(4, 5)]
    snapshot = game.snapshot()
    path = StrategiBFS.cari_jalur(snapshot, AI_ID)
    assert path is not None and path[0] is Direction.DOWN
    assert path[0] in snapshot.legal_moves_for(AI_ID)


def test_ucs_prefers_open_space_over_hugging_the_wall() -> None:
    game = GameEngine(GameConfig(rows=10, columns=10), rng=random.Random(1))
    # Head sits on the top wall; the apple is along the wall to the right.
    game.snakes[AI_ID] = SnakeState(AI_ID, [(2, 0), (1, 0), (0, 0)], Direction.RIGHT)
    game.apples = [(7, 1)]
    snapshot = game.snapshot()
    bfs_path = StrategiBFS.cari_jalur(snapshot, AI_ID)
    result = StrategiUCS.cari_jalur(snapshot, AI_ID)
    assert bfs_path is not None and result is not None
    cost, ucs_path = result
    # UCS drops away from the wall first, BFS takes the first shortest path.
    assert ucs_path[0] is Direction.DOWN
    assert len(ucs_path) >= len(bfs_path)
    assert cost >= len(ucs_path)


def test_search_strategies_survive_when_no_apple_is_reachable() -> None:
    game = GameEngine(GameConfig(rows=10, columns=10), rng=random.Random(1))
    game.snakes[AI_ID] = SnakeState(AI_ID, [(5, 5), (4, 5), (3, 5)], Direction.RIGHT)
    game.apples = [(0, 0)]
    # Enclose the apple with an opponent-like wall by using a second snake.
    game.snakes["other"] = SnakeState("other", [(1, 0), (1, 1), (0, 1)], Direction.UP)
    snapshot = game.snapshot()
    assert StrategiBFS.cari_jalur(snapshot, AI_ID) is None
    assert StrategiUCS.cari_jalur(snapshot, AI_ID) is None
    for strategy in (StrategiBFS(), StrategiUCS()):
        assert strategy.choose_move(snapshot, AI_ID, random.Random()) in snapshot.legal_moves_for(AI_ID)


def test_search_strategies_play_a_full_game_without_illegal_moves() -> None:
    for strategy_class in (StrategiBFS, StrategiUCS):
        game = GameEngine(GameConfig(rows=12, columns=12, apple_count=10), rng=random.Random(7))
        strategy = strategy_class()
        while game.status.value == "running":
            snapshot = game.snapshot()
            move = strategy.choose_move(snapshot, AI_ID, random.Random(0))
            assert game.step(AI_ID, move).accepted
        assert game.snakes[AI_ID].score > 0
