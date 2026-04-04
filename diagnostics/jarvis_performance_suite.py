import sys
import os
import time
import struct
import random
import threading
import psutil

print("=============================================")
print("  JARVIS-X AUTOMATED E2E PERFORMANCE SUITE   ")
print("=============================================\n")

def check_memory_performance():
    from memory.database import MemoryDB
    from memory.memory_store import cosine_similarity
    
    print("[1] STRESS TESTING NATIVE NUMPY VDB")
    test_db_path = "memory/bench_jarvis.db"
    
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
        
    db = MemoryDB(test_db_path)
    
    # 1. Insertion Test
    print("    -> Generating 2000 mock 768-D vectors...")
    vectors = []
    for _ in range(2000):
        mock_vec = [random.uniform(-1, 1) for _ in range(768)]
        blob = struct.pack(f'{len(mock_vec)}f', *mock_vec)
        vectors.append(blob)
        
    start_time = time.perf_counter()
    for idx, v in enumerate(vectors):
        db.add_interaction("user", f"mock {idx}", "context", v)
    insert_time = time.perf_counter() - start_time
    
    print(f"    -> INSERT TIME (2000 rows): {insert_time:.3f} seconds ({(2000/insert_time):.0f} inserts/sec)")
    
    # Check DB File Size
    db_size = os.path.getsize(test_db_path) / (1024 * 1024)
    print(f"    -> DATABASE SIZE ON DISK: {db_size:.2f} MB")
    
    # 2. Retrieval Test
    query_vec = [random.uniform(-1, 1) for _ in range(768)]
    query_blob = struct.pack(f'{len(query_vec)}f', *query_vec)
    
    start_time = time.perf_counter()
    embeddings = db.get_all_embeddings()
    fetch_time = time.perf_counter() - start_time
    
    print(f"    -> FETCH TIME (2000 vectors): {fetch_time:.3f} seconds")
    
    import numpy as np
    start_time = time.perf_counter()
    query_np = np.array(query_vec, dtype=np.float32)
    scores = []
    
    for row in embeddings:
        blob = row["embedding"]
        vec_tuple = struct.unpack(f'{len(blob)//4}f', blob)
        vec_np = np.array(vec_tuple, dtype=np.float32)
        score = np.dot(query_np, vec_np) / (np.linalg.norm(query_np) * np.linalg.norm(vec_np))
        scores.append((row["content"], score))
        
    scores.sort(key=lambda x: x[1], reverse=True)
    score_time = time.perf_counter() - start_time
    
    print(f"    -> COSINE SEARCH TIME (Numpy Dot Product): {score_time:.4f} seconds!")
    print(f"       (Top similarity score: {scores[0][1]:.3f})")
    
    del db
    try:
        os.remove(test_db_path)
    except: pass
    print()

def check_skill_discovery():
    print("[2] BENCHMARKING SKILL DISCOVERY (HOT-RELOAD)")
    try:
        from skills import discover_skills
        start_time = time.perf_counter()
        discover_skills(log_results=False)
        duration = time.perf_counter() - start_time
        print(f"    -> HOT RELOAD TIME: {duration:.4f} seconds")
    except Exception as e:
        print(f"    -> FAILED: {e}")
    print()

def check_system_monitor():
    print("[3] TESTING IRON MAN SYSTEM MONITOR BACKGROUND OVERHEAD")
    import psutil
    process = psutil.Process()
    base_mem = process.memory_info().rss / (1024*1024)
    
    print(f"    -> JAVRIS IDLE RAM: {base_mem:.2f} MB")
    
    try:
        from triggers.system_monitor import SystemMonitor
        from utils.events import EventBus
        bus = EventBus()
        sys_mon = SystemMonitor(bus)
        sys_mon.start()
        
        time.sleep(1) # Let monitor run
        active_mem = process.memory_info().rss / (1024*1024)
        
        print(f"    -> JARVIS + MONITOR RAM: {active_mem:.2f} MB")
        print(f"    -> DIFFERENTIAL OVERHEAD: {(active_mem - base_mem):.2f} MB")
        sys_mon.stop()
    except Exception as e:
        print(f"    -> FAILED: {e}")
    print()

def check_app_boot():
    print("[4] MEASURING JARVIS CORE INSTANTIATION TIME")
    try:
        from core.app import JarvisVirtualAssistant
        start_time = time.perf_counter()
        # Suppress logging
        import logging
        logging.getLogger().setLevel(logging.CRITICAL)
        
        app = JarvisVirtualAssistant(config={})
        boot_time = time.perf_counter() - start_time
        print(f"    -> APP COLD BOOT: {boot_time:.3f} seconds")
    except Exception as e:
        print(f"    -> APP BOOT FAILED (Probably missing keys/hw): {e}")
    print()

if __name__ == "__main__":
    check_memory_performance()
    check_skill_discovery()
    check_system_monitor()
    check_app_boot()
    print("=============================================")
    print("           ALL TESTS COMPLETED               ")
    print("=============================================")
