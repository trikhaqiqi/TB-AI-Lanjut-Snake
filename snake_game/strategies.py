from __future__ import annotations

import heapq
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Callable
from random import Random

from .models import Direction, GameSnapshot
from .models import Direction, GameSnapshot, Position

import time


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
        snake = snapshot.snake(snake_id)
        #Cek Beberapa output saat snake berpindah posisi
        print(snake.direction)
        print(f"Legal moves: {legal} \n")
        print(f"Snake Body: {snake.body} \n")
        print(f"Snake Direction Vector: {snake.direction.vector} \n")

        print(f"Posisi Apel: {snapshot.apples}")

        print(f"Apel [0]: {snapshot.apples[0]}")


        def apel_terdekat():
            x, y=snake.body[0]

            apel_dekat = ()
            h_dekat=9999
            for apel in snapshot.apples:
                x_apel, y_apel =  apel
                h = abs(x-x_apel)+abs(y-y_apel)
                if(h<h_dekat):
                    h_dekat=h
                    apel_dekat=apel
            return apel_dekat      

        apel_terdekat=apel_terdekat()
        print(f"Apel Terdekat: {apel_terdekat}")      

        #debug untuk mengetahui jumlah kolom dan baris papan
        print(f"jumlah kolom : {snapshot.columns}")
        print(f"jumlah baris : {snapshot.rows}")        

        print(f"Uler: {snapshot.snake}")

        # Note hasil cek output untuk setiap pergerakan:
        # Direction.UP: (0,-1)
        # Direction.DOWN : (0,1)
        # Direction.LEFT : (-1,0)
        # Direction.RIGHT : (1,0)

        #Penamaan Kotak untuk mendatar 0-N
        #Penamaan Kotak untuk Vertikal dari atas 0-N
        
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


@register_strategy("DFS")
class DFS(MoveStrategy):
    
    def __init__(self):
        self.number_of_expanded = 0
        self.number_of_generated = 0
        self.path_length = 0
        self.total_apel=0
        self.visited= []
        self.path_dfs=[]
        self.execution_time = 0.0
        self.total_execution_time = 0.0
    
    def choose_move(self, snapshot, snake_id, rng) -> Direction:
        legal_moves = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        print(f"===Ronde {snapshot.rounds_completed}====")

        start_time = time.perf_counter()
        self.execution_time = time.perf_counter() - start_time
        self.total_execution_time += self.execution_time

        head_x, head_y = snake.body[0]
        self.visited.append((head_x,head_y))
        self.path_dfs.append((head_x,head_y))

        self.number_of_expanded+=1
        self.path_length=len(self.path_dfs)

        if(snapshot.rounds_completed==0):
            self.total_apel=len(snapshot.apples)

        #Urutan arah prioritas adalah maju, belok kanan, belok kiri
        if snake.direction==Direction.RIGHT:
            priority_moves=[Direction.RIGHT, Direction.DOWN, Direction.UP]
        elif snake.direction==Direction.LEFT:
            priority_moves=[Direction.LEFT, Direction.UP, Direction.DOWN]
        elif snake.direction==Direction.UP:
            priority_moves=[Direction.UP, Direction.RIGHT, Direction.LEFT]
        else:
            priority_moves=[Direction.DOWN,Direction.LEFT, Direction.RIGHT]

        def is_visited(next):
            if next in self.visited:
                return True
            return False

        def cek_arah(direction):
            if(direction in legal_moves):
                return True

        def cek_kunjungan(x,y):
            if (x,y) not in self.visited:
                return True
            return False


        maju=snake.direction
        dx, dy = maju.vector


        print(f"Path_Length : {self.path_length}\n")
        print(f"Path DFS:{self.path_dfs}\n")
        print(f"Number of Expanded : {self.number_of_expanded}")
        print(f"Number of Generated: {self.number_of_generated}")
        print(f"Path Lenght: {self.path_length}")
        print(f"Jumlah Apel dimakan dari Total Apel: {snake.score}/{self.total_apel}")
        print(f"Success Rate : {(snake.score/self.total_apel)*100} persen")
        print(f"Execution Time : {self.total_execution_time* 1000:.4f}")

        if(legal_moves):
            self.number_of_generated+=len(legal_moves)
            
            if(maju in legal_moves and not is_visited(tuple((head_x+dx,head_y+dy)))):
                print ("masih bisa maju\n\n")
                return maju
            else:
                print("harusnya sudah ubah arah")
                for direction in priority_moves:
                    dirx,diry = direction.vector
                    islegalmove=cek_arah(direction)
                    isbelumdikunjungi=cek_kunjungan(head_x+dirx,head_y+diry)
                    
                    if(islegalmove and isbelumdikunjungi):
                        return direction
                print("habis langkah, perlu restart algoritma, biar game tetap jalan")
                
                #clear visited
                self.visited.clear()
                
                #pilih random move
                return rng.choice(legal_moves)

@register_strategy("Minimax")
class Minimax(MoveStrategy):
    MAX_DEPTH = 5

    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:

        legal = snapshot.legal_moves_for(snake_id)
        if not legal:
            return snapshot.snake(snake_id).direction
            
        opponent_id = None
        index = 0
        while opponent_id is None:
            if snapshot.snakes[index].snake_id != snake_id:
                opponent_id = snapshot.snakes[index].snake_id
            index += 1
    
        best_value = float("-inf")
        best_moves = []

        for move in legal:
            new_snapshot = self._expand_snapshot(snapshot, snake_id, move, opponent_id)
            value = self._minimax(self.MAX_DEPTH - 1, new_snapshot, True, snake_id, opponent_id)

            if value > best_value:
                best_value = value
                best_moves = [move]
            elif value == best_value:
                best_moves.append(move)

        return rng.choice(best_moves)

    def _minimax(self, curDepth, snapshot, opponents_turn, snake_id, opponent_id):
        if not snapshot.apples:
            return 100 * (snapshot.snake(snake_id).score - snapshot.snake(opponent_id).score)
                        
        if curDepth == 0:
            return 100 * (snapshot.snake(snake_id).score - snapshot.snake(opponent_id).score) + self._distance_heuristic(snapshot, snake_id, opponent_id)
            
        if opponents_turn:
            legal = snapshot.legal_moves_for(opponent_id)
            if not legal:
                return float("inf")
            values = []

            for move in legal:
                new_snapshot = self._expand_snapshot(snapshot, opponent_id, move, snake_id)
                value = self._minimax(curDepth - 1, new_snapshot, False, snake_id, opponent_id)
                values.append(value)

            return min(values)
        else:
            legal = snapshot.legal_moves_for(snake_id)
            if not legal:
                return float("-inf")
            
            values = []

            for move in legal:
                new_snapshot = self._expand_snapshot(snapshot, snake_id, move, opponent_id)
                value = self._minimax(curDepth - 1, new_snapshot, True, snake_id, opponent_id)
                values.append(value)
                                
            return max(values)   

    def _distance_heuristic(self, snapshot, snake_id, opponent_id):
        snake = snapshot.snake(snake_id)
        opponent = snapshot.snake(opponent_id)

        lowest_distance = float('-inf')
        for apple in snapshot.apples:
            snake_distance = abs(snake.body[0][0] - apple[0]) + abs(snake.body[0][1] - apple[1])
            opponent_distance = abs(opponent.body[0][0] - apple[0]) + abs(opponent.body[0][1] - apple[1])
            if (((2 * snake_distance) - opponent_distance) * -1) > lowest_distance:
                lowest_distance = ((2* snake_distance) - opponent_distance) * -1

        return lowest_distance
        
    def _expand_snapshot(self, snapshot, snake_id, move, next_snake_id):
        snake = snapshot.snake(snake_id)

        dx, dy = move.vector
        new_head = (
            snake.body[0][0] + dx,
            snake.body[0][1] + dy
        )

        new_body = [new_head] + list(snake.body)
        new_apples = list(snapshot.apples)
        new_score = snake.score

        if new_head in new_apples:
            new_apples.remove(new_head)
            new_score += 1
        else:
            new_body.pop()

        new_snakes = []
        for current_snake in snapshot.snakes:
            if current_snake.snake_id == snake_id:
                new_snakes.append(
                    type(current_snake)(
                        snake_id=current_snake.snake_id,
                        body=tuple(new_body),
                        direction=move,
                        score=new_score
                    )
                )
            else:
                new_snakes.append(current_snake)

        new_legal_moves = []
        for current_snake in new_snakes:
            current_legal = []

            for direction in Direction:
                if (len(current_snake.body) > 1 and direction == current_snake.direction.opposite):
                    continue

                dx, dy = direction.vector
                x, y = current_snake.body[0][0] + dx, current_snake.body[0][1] + dy

                if (x < 0 or x >= snapshot.columns or y < 0 or y >= snapshot.rows):
                    continue

                growing = (x, y) in new_apples
                if growing:
                    own_body = current_snake.body
                else:
                    own_body = current_snake.body[:-1]

                if (x, y) in own_body:
                    continue

                collision = False
                for other_snake in new_snakes:
                    if other_snake.snake_id != current_snake.snake_id:
                        if (x, y) in other_snake.body:
                            collision = True

                if not collision:
                    current_legal.append(direction)

            new_legal_moves.append((current_snake.snake_id, tuple(current_legal)))

        return GameSnapshot(
            rows=snapshot.rows,
            columns=snapshot.columns,
            snakes=tuple(new_snakes),
            apples=tuple(new_apples),
            rounds_completed=snapshot.rounds_completed,
            rounds_remaining=snapshot.rounds_remaining,
            active_snake_id=next_snake_id,
            legal_moves=tuple(new_legal_moves)
        )

@register_strategy("Minimax AB Pruning")
class MiniMaxABPruning(Minimax):
    MAX_DEPTH = 10

    def choose_move(
            self, snapshot: GameSnapshot, snake_id: str, rng: Random
        ) -> Direction:
    
            legal = snapshot.legal_moves_for(snake_id)
            if not legal:
                return snapshot.snake(snake_id).direction
                
            opponent_id = None
            index = 0
            while opponent_id is None:
                if snapshot.snakes[index].snake_id != snake_id:
                    opponent_id = snapshot.snakes[index].snake_id
                index += 1
        
            best_value = float("-inf")
            best_moves = []
    
            for move in legal:
                new_snapshot = self._expand_snapshot(snapshot, snake_id, move, opponent_id)
                value = self._minimax(self.MAX_DEPTH - 1, new_snapshot, True, snake_id, opponent_id, float("-inf"), float("inf"))
    
                if value > best_value:
                    best_value = value
                    best_moves = [move]
                elif value == best_value:
                    best_moves.append(move)
    
            return rng.choice(best_moves)

    def _minimax(self, curDepth, snapshot, opponents_turn, snake_id, opponent_id, alpha, beta):
        if not snapshot.apples:
            return 100 * (snapshot.snake(snake_id).score - snapshot.snake(opponent_id).score)
                        
        if curDepth == 0:
            return 100 * (snapshot.snake(snake_id).score - snapshot.snake(opponent_id).score) + self._distance_heuristic(snapshot, snake_id, opponent_id)
                    
        if opponents_turn:
            best_value = float("inf")

            legal = snapshot.legal_moves_for(opponent_id)
            if not legal:
                return float("inf")

            for move in legal:
                new_snapshot = self._expand_snapshot(snapshot, opponent_id, move, snake_id)
                value = self._minimax(curDepth - 1, new_snapshot, False, snake_id, opponent_id, alpha, beta)
                best_value = min(best_value, value)
                beta = min(beta, best_value)

                if alpha >= beta:
                    break
            
            return best_value
        else:
            best_value = float("-inf")

            legal = snapshot.legal_moves_for(snake_id)
            if not legal:
                return float("-inf")

            for move in legal:
                new_snapshot = self._expand_snapshot(snapshot, snake_id, move, opponent_id)
                value = self._minimax(curDepth - 1, new_snapshot, True, snake_id, opponent_id, alpha, beta)

                best_value = max(best_value, value)
                alpha = max(alpha, best_value)

                if alpha >= beta:
                    break
                                
            return best_value 


@register_strategy("A*")
class Astar(MoveStrategy):
    def __init__(self):
            # statistik
            self.number_of_expanded = 0
            self.number_of_generated = 0
            self.path_length = 0
            self.path_cost=0
            self.path = []

            self.execution_time = 0.0       
            self.total_execution_time = 0.0 
            self.move_count = 0

            self.total_path_length = 0
            self.total_path_cost = 0
            self.current_target = None
            self.max_path_length_target = 0
            self.max_path_cost_target = 0
            
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        legal = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        if not legal or not snapshot.apples:
            return snake.direction

        start_time = time.perf_counter()

        start = snake.body[0]
        apples = snapshot.apples
        expanded=set()
      

        #fungsi hitung heuristik
        def hitung_h(x,y):
            h_min=9999
            for apel in apples:
                x_apel, y_apel = apel
                jarak = abs(x-x_apel)+abs(y-y_apel)
                if(jarak<h_min):
                    h_min=jarak
            return h_min

        x_start, y_start = start
        h_start=hitung_h(x_start,y_start)
        
        g_start=0
        f_start=g_start+h_start
        # print(f"h_start: {h_start}, g_start: {g_start}, f_start:{h_start}")
        open_list = [(f_start, g_start, h_start, start)]

        goal = None
        parent = {start: None}
        best_g = {start: 0}
        # print(f"open_list :{open_list}")

        while(len(open_list) > 0 ):
            best_i = 0
            for i in range(len(open_list)):
                f_i, g_i, h_i, pos_i = open_list[i]
                f_best, g_best, h_best, pos_best = open_list[best_i]
                if f_i < f_best:
                    best_i = i
                if f_i == f_best and h_i < h_best:
                    best_i = i
            
            
            f, g, h, current = open_list.pop(best_i)
            
            if current in expanded:
                continue

            #Ekspansi node ini
            expanded.add(current)
            self.number_of_expanded+=1
            # print(f"expanded: {self.number_of_expanded}")
            if current in apples:
                goal = current
                break

            x_current, y_current = current
            for arah in Direction:
                if current == start and arah not in legal:
                    continue

                dx, dy =  arah.vector
                x_next = x_current + dx
                y_next = y_current + dy

                next = (x_next, y_next)
                if next in snake.body:
                    continue

                if next in expanded:
                    continue

                g_new = g+1

                if next in best_g and g_new >= best_g[next]:
                    continue
            
                best_g[next] = g_new
                parent[next] = current
                # print(f"parent: {parent[next]}")

                self.number_of_generated+=1
                h_new= hitung_h(x_next, y_next)
                f_new = g_new + h_new

                open_list.append((f_new, g_new, h_new, next))

        
        self.execution_time = time.perf_counter() - start_time
        self.total_execution_time += self.execution_time
        self.move_count+=1

        
        # print(f"Goal: {goal}")
        if goal == None:
            return rng.choice(list(legal))

        path = []
        node = goal
        while node != start:
            path.append(node)
            node = parent[node]
        path.reverse()

        self.path=path
        self.path_length = len(path)
        self.path_cost = best_g[goal]
        self.total_path_cost+=1

        if goal != self.current_target:
            self.current_target = goal
            self.max_path_length_target = self.path_length
            self.total_path_length += self.path_length
        elif self.path_length > self.max_path_length_target:
                self.total_path_length += self.path_length - self.max_path_length_target
                self.max_path_length_target = self.path_length


        #Statistik
        print("")
        print(f"Total Path Length : {self.total_path_length}")
        print(f"Total Path Cost : {self.total_path_cost}")
        print(f"Jumlah langkah dihitung : {self.move_count}")
        print(f"Total expanded (total)   : {self.number_of_expanded}")
        print(f"Total generated (total)  : {self.number_of_generated}")
        print(f"Total execution time    : {self.total_execution_time * 1000:.4f} ms")

        if not path:
            return snake.direction

        x_first, y_first = path[0]
        dx, dy = x_first - x_start, y_first-y_start
        for arah in legal:
            if arah.vector == (dx, dy):
                return arah



        return rng.choice(list(legal))




@register_strategy("Greedy Best-First Search")
class GreedyBFS(MoveStrategy):
    def __init__(self):
            # statistik
            self.number_of_expanded = 0
            self.number_of_generated = 0
            self.path_length = 0
            self.path_cost=0
            self.path = []

            self.execution_time = 0.0       
            self.total_execution_time = 0.0 
            self.move_count = 0

            self.total_path_length = 0
            self.total_path_cost = 0
            self.current_target = None
            self.max_path_length_target = 0
            self.max_path_cost_target = 0
            
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        legal = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        if not legal or not snapshot.apples:
            return snake.direction

        start_time = time.perf_counter()

        start = snake.body[0]
        apples = snapshot.apples
        expanded=set()
      

        #fungsi hitung heuristik
        def hitung_h(x,y):
            h_min=9999
            for apel in apples:
                x_apel, y_apel = apel
                jarak = abs(x-x_apel)+abs(y-y_apel)
                if(jarak<h_min):
                    h_min=jarak
            return h_min

        x_start, y_start = start
        h_start=hitung_h(x_start,y_start)
        
        g_start=0
        f_start=h_start
        # print(f"h_start: {h_start}, g_start: {g_start}, f_start:{h_start}")
        open_list = [(f_start, g_start, h_start, start)]

        goal = None
        parent = {start: None}
        best_g = {start: 0}
        # print(f"open_list :{open_list}")

        while(len(open_list) > 0 ):
            best_i = 0
            for i in range(len(open_list)):
                f_i, g_i, h_i, pos_i = open_list[i]
                f_best, g_best, h_best, pos_best = open_list[best_i]
                if f_i < f_best:
                    best_i = i
                if f_i == f_best and h_i < h_best:
                    best_i = i
            
            
            f, g, h, current = open_list.pop(best_i)
            
            if current in expanded:
                continue

            #Ekspansi node ini
            expanded.add(current)
            self.number_of_expanded+=1
            # print(f"expanded: {self.number_of_expanded}")
            if current in apples:
                goal = current
                break

            x_current, y_current = current
            for arah in Direction:
                if current == start and arah not in legal:
                    continue

                dx, dy =  arah.vector
                x_next = x_current + dx
                y_next = y_current + dy

                next = (x_next, y_next)
                if next in snake.body:
                    continue

                if next in expanded:
                    continue

                g_new = g+1

                # if next in best_g and g_new >= best_g[next]:
                #     continue
            
                best_g[next] = g_new
                parent[next] = current
                # print(f"parent: {parent[next]}")

                self.number_of_generated+=1
                h_new= hitung_h(x_next, y_next)
                f_new = h_new

                open_list.append((f_new, g_new, h_new, next))

        
        self.execution_time = time.perf_counter() - start_time
        self.total_execution_time += self.execution_time
        self.move_count+=1

        
        # print(f"Goal: {goal}")
        if goal == None:
            return rng.choice(list(legal))

        path = []
        node = goal
        while node != start:
            path.append(node)
            node = parent[node]
        path.reverse()

        self.path=path
        self.path_length = len(path)
        self.path_cost = best_g[goal]
        self.total_path_cost+=1

        if goal != self.current_target:
            self.current_target = goal
            self.max_path_length_target = self.path_length
            self.total_path_length += self.path_length
        elif self.path_length > self.max_path_length_target:
                self.total_path_length += self.path_length - self.max_path_length_target
                self.max_path_length_target = self.path_length


        #Statistik
        print("")
        print(f"Total Path Length : {self.total_path_length}")
        print(f"Total Path Cost : {self.total_path_cost}")
        print(f"Jumlah langkah dihitung : {self.move_count}")
        print(f"Total expanded (total)   : {self.number_of_expanded}")
        print(f"Total generated (total)  : {self.number_of_generated}")
        print(f"Total execution time    : {self.total_execution_time * 1000:.4f} ms")

        if not path:
            return snake.direction

        x_first, y_first = path[0]
        dx, dy = x_first - x_start, y_first-y_start
        for arah in legal:
            if arah.vector == (dx, dy):
                return arah



        return rng.choice(list(legal))
