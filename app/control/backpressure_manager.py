from __future__ import annotations
import asyncio,time
from collections import deque
class BackpressureManager:
    def __init__(self,window_seconds:int=60,limit_rho:float=0.95):
        self.window_seconds=window_seconds; self.limit_rho=limit_rho
        self.arrivals=deque(); self.completions=deque(); self._lock=asyncio.Lock()
    async def record_arrival(self)->None:
        now=time.time();
        async with self._lock:
            self.arrivals.append(now); self._prune(now)
    async def record_completion(self)->None:
        now=time.time();
        async with self._lock:
            self.completions.append(now); self._prune(now)
    async def is_overloaded(self)->bool:
        now=time.time()
        async with self._lock:
            self._prune(now); lam=len(self.arrivals)/self.window_seconds; mu=len(self.completions)/self.window_seconds
        if mu==0: return lam>0
        return (lam/mu)>=self.limit_rho
    def _prune(self,current_time:float)->None:
        cutoff=current_time-self.window_seconds
        while self.arrivals and self.arrivals[0]<cutoff: self.arrivals.popleft()
        while self.completions and self.completions[0]<cutoff: self.completions.popleft()
