from __future__ import annotations

import heapq
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Callable
from random import Random

from .models import Direction, GameSnapshot, Position


class MoveStrategy(ABC):
    """Base class for every automated snake movement method."""

    @abstractmethod
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        """Return the direction for ``snake_id`` for the current turn."""


STRATEGY_REGISTRY: dict[str, type[MoveStrategy]] = {}


def register_strategy(name: str) -> Callable[[type[MoveStrategy]], type[MoveStrategy]]:
    """Register a strategy class so it appears in the setup-screen dropdown."""

    def decorator(strategy_class: type[MoveStrategy]) -> type[MoveStrategy]:
        if not name.strip():
            raise ValueError("Strategy names cannot be empty.")
        STRATEGY_REGISTRY[name] = strategy_class
        return strategy_class

    return decorator


def create_strategy(name: str) -> MoveStrategy:
    try:
        return STRATEGY_REGISTRY[name]()
    except KeyError as exc:
        raise ValueError(f"Unknown strategy: {name}") from exc


@register_strategy("Safe Random")
class SafeRandomStrategy(MoveStrategy):
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        legal = snapshot.legal_moves_for(snake_id)
        if legal:
            return rng.choice(legal)
        return snapshot.snake(snake_id).direction


@register_strategy("Greedy")
class GreedyStrategy(MoveStrategy):
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        legal = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        if not legal or not snapshot.apples:
            return snake.direction

        head_x, head_y = snake.body[0]

        def distance(direction: Direction) -> int:
            dx, dy = direction.vector
            new_x, new_y = head_x + dx, head_y + dy
            return min(
                abs(new_x - apple_x) + abs(new_y - apple_y)
                for apple_x, apple_y in snapshot.apples
            )

        best_distance = min(distance(direction) for direction in legal)
        best_moves = [direction for direction in legal if distance(direction) == best_distance]
        return rng.choice(best_moves)


def _di_dalam_arena(snapshot: GameSnapshot, sel: Position) -> bool:
    x, y = sel
    return 0 <= x < snapshot.columns and 0 <= y < snapshot.rows


def _tetangga(sel: Position, arah: Direction) -> Position:
    dx, dy = arah.vector
    return sel[0] + dx, sel[1] + dy


def _waktu_rintangan(snapshot: GameSnapshot, snake_id: str) -> dict[Position, int]:
    # Petakan setiap sel terisi ke jumlah langkah sampai sel itu kosong
    terblokir_selamanya = snapshot.rows * snapshot.columns + 1
    waktu: dict[Position, int] = {}
    for ular in snapshot.snakes:
        if ular.snake_id != snake_id:
            for segmen in ular.body:
                waktu[segmen] = terblokir_selamanya
    badan_sendiri = snapshot.snake(snake_id).body
    for indeks, segmen in enumerate(badan_sendiri):
        # Segmen ke-indeks kosong setelah len(badan) - indeks langkah.
        waktu[segmen] = max(waktu.get(segmen, 0), len(badan_sendiri) - indeks)
    return waktu


def _sel_kosong(
    snapshot: GameSnapshot, waktu: dict[Position, int], sel: Position, langkah: int
) -> bool:
    return _di_dalam_arena(snapshot, sel) and waktu.get(sel, 0) <= langkah


def _luas_area_terjangkau(snapshot: GameSnapshot, snake_id: str, awal: Position) -> int:
    # Hitung sel yang dapat dicapai dari awal (flood fill) untuk cadangan
    waktu = _waktu_rintangan(snapshot, snake_id)
    dikunjungi = {awal}
    antrean = deque([(awal, 1)])
    while antrean:
        sel, langkah = antrean.popleft()
        for arah in Direction:
            berikutnya = _tetangga(sel, arah)
            if berikutnya not in dikunjungi and _sel_kosong(
                snapshot, waktu, berikutnya, langkah + 1
            ):
                dikunjungi.add(berikutnya)
                antrean.append((berikutnya, langkah + 1))
    return len(dikunjungi)


def _langkah_bertahan(
    snapshot: GameSnapshot, snake_id: str, gerakan_sah: tuple[Direction, ...]
) -> Direction:
    # Jika tidak ada apel yang terjangkau, bergerak ke area terbuka terluas.
    kepala = snapshot.snake(snake_id).body[0]
    return max(
        gerakan_sah,
        key=lambda arah: _luas_area_terjangkau(
            snapshot, snake_id, _tetangga(kepala, arah)
        ),
    )


@register_strategy("BFS")
class StrategiBFS(MoveStrategy):
    # Breadth-First Search

    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        gerakan_sah = snapshot.legal_moves_for(snake_id)
        ular = snapshot.snake(snake_id)
        if not gerakan_sah:
            return ular.direction

        jalur = self.cari_jalur(snapshot, snake_id)
        if jalur:
            return jalur[0]
        return _langkah_bertahan(snapshot, snake_id, gerakan_sah)

    @staticmethod
    def cari_jalur(snapshot: GameSnapshot, snake_id: str) -> list[Direction] | None:
        # Kembalikan daftar gerakan terpendek menuju apel mana pun atau None
        kepala = snapshot.snake(snake_id).body[0]
        apel = set(snapshot.apples)
        waktu = _waktu_rintangan(snapshot, snake_id)

        # Frontier berupa antrean FIFO: simpul diekspansi berurutan per kedalaman.
        frontier: deque[tuple[Position, list[Direction]]] = deque()
        dikunjungi = {kepala}
        for arah in snapshot.legal_moves_for(snake_id):
            sel = _tetangga(kepala, arah)
            if sel in apel:
                return [arah]
            dikunjungi.add(sel)
            frontier.append((sel, [arah]))

        while frontier:
            sel, jalur = frontier.popleft()
            langkah = len(jalur)
            for arah in Direction:
                berikutnya = _tetangga(sel, arah)
                if berikutnya in dikunjungi or not _sel_kosong(
                    snapshot, waktu, berikutnya, langkah + 1
                ):
                    continue
                if berikutnya in apel:
                    return jalur + [arah]
                dikunjungi.add(berikutnya)
                frontier.append((berikutnya, jalur + [arah]))
        return None


@register_strategy("UCS")
class StrategiUCS(MoveStrategy):
    # Uniform-Cost Search

    BIAYA_LANGKAH = 1
    PENALTI_BAHAYA = 2

    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        gerakan_sah = snapshot.legal_moves_for(snake_id)
        ular = snapshot.snake(snake_id)
        if not gerakan_sah:
            return ular.direction

        hasil = self.cari_jalur(snapshot, snake_id)
        if hasil:
            _, jalur = hasil
            return jalur[0]
        return _langkah_bertahan(snapshot, snake_id, gerakan_sah)

    @classmethod
    def biaya_langkah(
        cls,
        snapshot: GameSnapshot,
        waktu: dict[Position, int],
        sel: Position,
        langkah: int,
    ) -> int:
        sisi_tertutup = sum(
            not _sel_kosong(snapshot, waktu, _tetangga(sel, arah), langkah + 1)
            for arah in Direction
        )
        return cls.BIAYA_LANGKAH + cls.PENALTI_BAHAYA * sisi_tertutup

    @classmethod
    def cari_jalur(
        cls, snapshot: GameSnapshot, snake_id: str
    ) -> tuple[int, list[Direction]] | None:
        # Kembalikan (biaya, gerakan) jalur termurah ke apel, atau None
        kepala = snapshot.snake(snake_id).body[0]
        apel = set(snapshot.apples)
        waktu = _waktu_rintangan(snapshot, snake_id)

        # Frontier berupa priority queue yang diurutkan menurut biaya kumulatif g(n).
        # Penghitung memecah seri sesuai urutan masuk agar hasilnya konsisten.
        frontier: list[tuple[int, int, Position, list[Direction]]] = []
        penghitung = 0
        biaya_terbaik: dict[Position, int] = {kepala: 0}
        for arah in snapshot.legal_moves_for(snake_id):
            sel = _tetangga(kepala, arah)
            biaya = cls.biaya_langkah(snapshot, waktu, sel, 1)
            biaya_terbaik[sel] = biaya
            heapq.heappush(frontier, (biaya, penghitung, sel, [arah]))
            penghitung += 1

        while frontier:
            biaya, _, sel, jalur = heapq.heappop(frontier)
            if biaya > biaya_terbaik.get(sel, biaya):
                continue  # Jalur yang lebih murah ke sel ini sudah diekspansi.
            # Uji tujuan saat ekspansi menjamin jalur yang ditemukan paling murah.
            if sel in apel:
                return biaya, jalur
            langkah = len(jalur)
            for arah in Direction:
                berikutnya = _tetangga(sel, arah)
                if not _sel_kosong(snapshot, waktu, berikutnya, langkah + 1):
                    continue
                biaya_baru = biaya + cls.biaya_langkah(
                    snapshot, waktu, berikutnya, langkah + 1
                )
                if biaya_baru < biaya_terbaik.get(berikutnya, biaya_baru + 1):
                    biaya_terbaik[berikutnya] = biaya_baru
                    heapq.heappush(
                        frontier, (biaya_baru, penghitung, berikutnya, jalur + [arah])
                    )
                    penghitung += 1
        return None


# Assignment template -------------------------------------------------------
# 1. Copy this class and give it a unique name.
# 2. Implement choose_move using only the immutable snapshot.
# 3. Add @register_strategy("My Strategy") above the class. It will then appear
#    automatically in the setup screen.
#
# @register_strategy("My Strategy")
# class MyStrategy(MoveStrategy):
#     def choose_move(self, snapshot, snake_id, rng):
#         legal_moves = snapshot.legal_moves_for(snake_id)
#         return legal_moves[0] if legal_moves else snapshot.snake(snake_id).direction
