from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from random import Random

from .models import Direction, GameSnapshot


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
    
    
    def choose_move(self, snapshot, snake_id, rng) -> Direction:
        legal_moves = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        print(f"===Ronde {snapshot.rounds_completed}====")
        #Simpan kotak yang sudah dikunjungi    
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
        print(f"Success Rate : {(snake.score/self.total_apel)*100} persen")

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

        
@register_strategy("AStar")
class AStar(MoveStrategy):
    def __init__(self):
        # statistik
        self.number_of_expanded = 0
        self.number_of_generated = 0
        self.path_length = 0
        self.path_astar = []

    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        legal = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        if len(legal) == 0 or len(snapshot.apples) == 0:
            return snake.direction

        start = snake.body[0]
        apples = snapshot.apples

        #Cek ilegal move
        blocked = set()
        for s in snapshot.snakes:
            if s.snake_id == snake_id:
                # ular sendiri: ekor tidak dihitung, karena akan bergeser
                for i in range(len(s.body) - 1):
                    blocked.add(s.body[i])
            else:
                # ular lawan: seluruh badan dihitung
                for posisi in s.body:
                    blocked.add(posisi)

        # Cek apakah kotak (x, y) masih di dalam papan
        def di_dalam_papan(x, y):
            if x < 0:
                return False
            if x >= snapshot.columns:
                return False
            if y < 0:
                return False
            if y >= snapshot.rows:
                return False
            return True

        # Cek apakah kotak (x, y) boleh dilewati
        def boleh_dilewati(x, y):
            if not di_dalam_papan(x, y):
                return False
            if (x, y) in blocked:
                return False
            return True

        # Heuristik h: jarak Manhattan ke apel terdekat
        def hitung_h(x, y):
            h_terkecil = 9999
            for apel in apples:
                apel_x, apel_y = apel
                jarak = abs(x - apel_x) + abs(y - apel_y)
                if jarak < h_terkecil:
                    h_terkecil = jarak
            return h_terkecil

        # inisial state
        start_x, start_y = start
        h_start = hitung_h(start_x, start_y)

        # Setiap isi open_list: (f, g, h, posisi)
        open_list = [(h_start, 0, h_start, start)]

        g_cost = {}
        g_cost[start] = 0

        parent_posisi = {}
        parent_arah = {}
        parent_posisi[start] = None

        closed = set()              # posisi yang sudah diekspansi
        goal = None

        expanded_giliran = 0
        generated_giliran = 0
        urutan_expand = []          # untuk dicetak: (posisi, g, h, f)

       

        #Loop A*

        while len(open_list) > 0:

            #Cari node dengan f terkecil (kalau f sama, pilih h terkecil)
            best_i = 0
            for i in range(len(open_list)):
                f_i, g_i, h_i, pos_i = open_list[i]
                f_best, g_best, h_best, pos_best = open_list[best_i]
                if f_i < f_best:
                    best_i = i
                if f_i == f_best and h_i < h_best:
                    best_i = i

            #Keluarkan node terpilih dari open_list
            f, g, h, current = open_list.pop(best_i)

            #Lewati kalau sudah pernah diekspansi
            if current in closed:
                continue

            #Ekspansi node ini
            closed.add(current)
            expanded_giliran += 1
            urutan_expand.append((current, g, h, f))

            #ular makan apel
            if current in apples:
                goal = current
                break

            current_x, current_y = current
            for arah in Direction:
                # langkah pertama harus mengikuti legal moves dari engine
                if current == start and arah not in legal:
                    continue

                dx, dy = arah.vector
                next_x = current_x + dx
                next_y = current_y + dy
                tetangga = (next_x, next_y)

                if not boleh_dilewati(next_x, next_y):
                    continue
                if tetangga in closed:
                    continue

                g_baru = g + 1                          # biaya dari start ke tetangga
                h_baru = hitung_h(next_x, next_y)       # estimasi tetangga ke apel
                f_baru = g_baru + h_baru

                # simpan kalau tetangga baru, atau ketemu jalan yang lebih murah
                if tetangga not in g_cost or g_baru < g_cost[tetangga]:
                    g_cost[tetangga] = g_baru
                    parent_posisi[tetangga] = current
                    parent_arah[tetangga] = arah
                    open_list.append((f_baru, g_baru, h_baru, tetangga))
                    generated_giliran += 1

            print(f"Open List : {open_list}")
            print(f"Closed List : {closed}")
            

        self.number_of_expanded += expanded_giliran
        self.number_of_generated += generated_giliran
        # print(f"Goal : {goal}")
  
        #Kalau tidak ada jalur ke apel
        if goal == None:
            pilihan = legal[0]
            ruang_terbanyak = -1
            for arah in legal:
                dx, dy = arah.vector
                x = start_x + dx
                y = start_y + dy

                # hitung kotak kosong di sekitar (x, y)
                ruang = 0
                for arah_sekitar in Direction:
                    sx, sy = arah_sekitar.vector
                    if boleh_dilewati(x + sx, y + sy):
                        ruang += 1

                if ruang > ruang_terbanyak:
                    ruang_terbanyak = ruang
                    pilihan = arah

            print(f"Tidak ada jalur ke apel, pilih {pilihan.name}")
            return pilihan

        #Susun jalur
        jalur_posisi = []
        jalur_arah = []
        node = goal
        while parent_posisi[node] != None:
            jalur_posisi.insert(0, node)
            jalur_arah.insert(0, parent_arah[node])
            node = parent_posisi[node]

        self.path_astar = jalur_posisi
        self.path_length += 1
        langkah = jalur_arah[0]

        teks_jalur = ""
        for arah in jalur_arah:
            if teks_jalur != "":
                teks_jalur += " -> "
            teks_jalur += arah.name

        #Cetak proses A* ronde ini
        print(f"Apel   : {goal}")
        print(f"Jalur  : {teks_jalur}")
        print(f"Pilih  : {langkah.name}")
        print(f"\n===== Ronde {snapshot.rounds_completed} =====")
        print(f"Kepala : {start}")
        print(f"Node yang diekspansi ({expanded_giliran}):")
        nomor = 1
        for data in urutan_expand:
            posisi, g, h, f = data
            print(f"  {nomor}. {posisi}  g={g} h={h} f={f}")
            nomor += 1
        print(f"Generated: {generated_giliran}")

        return langkah
