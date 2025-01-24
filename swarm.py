from __future__ import annotations

from typing import Callable, Any
from collections.abc import Collection
from enum import Enum

import asyncio

import time
import functools

class ModeFlight(Enum):
    TakeOff = 0
    Landing = 1


async def _async_takeoff(drone: Drone) -> None:
    # codrone_edu.droneのDroneクラスのtakeoff関数をasyncとして再作成
    drone.reset_move_values()
    drone.sendTakeOff()

    timeout = 4
    init_time = time.time()
    while time.time() - init_time < timeout:
        if drone.get_state_data()[2] is ModeFlight.TakeOff:
            break
        else:
            await asyncio.sleep(0.01)
    await asyncio.sleep(4)


async def _async_land(drone: Drone) -> None:
    # codrone_edu.droneのDroneクラスのland関数をasyncとして再作成
    drone.reset_move_values()
    drone.previous_land[0] = drone.previous_land[0] + drone.get_position_data()[1]
    drone.previous_land[1] = drone.previous_land[1] + drone.get_position_data()[2]
    drone.sendLanding()

    timeout = 4
    init_time = time.time()
    while time.time() - init_time < timeout:
        if drone.get_state_data()[2] is ModeFlight.Landing:
            break
        else:
            drone.sendLanding()
            await asyncio.sleep(0.01)

    await asyncio.sleep(4)


class Swarm:
    _drones: dict[str, Drone]

    def __init__(self) -> None:
        self._drones = dict()

    def _wrapper(self: Swarm, attribute: str, *args, **kwargs) -> Any | None:
        # Wrapper function to repeat any drone operation on all the (specified) drones in the swarm.
        # スウォーム内の全ての（指定された）ドローンに対して、任意のドローン操作を繰り返すラッパー関数。
        drones = kwargs.get("drones")

        if not drones:
            # ユーザーがドローンを指定していない場合すべてのドローンを選択。
            drones = self._drones.values()
        else:
            del kwargs["drones"]
            if isinstance(drones[0], str):
                drones = [self._drones[port] for port in drones]
            else:
                drones = [drone for drone in self._drones.values() if drone in drones]

        retval = [getattr(drone, attribute)(*args, **kwargs) for drone in drones]
        if any(retval):
            return retval
        else:
            return None

    def __getattr__(self, name: str) -> Callable | list[tuple]:
        """
        Makes it so that you can call any function in  a Drone object with the Swarm
        object and it works normally for all/set number of drones.
        """
        """
        Droneの関数をSwarmオブジェクトからも使えるようにする。
        """
        if not self._drones:
            raise ValueError("スウォームにドローンなし")

        if name not in dir(self):
            for _, drone in self._drones.items():
                # getting first value
                break

            if callable(getattr(drone, name)):
                return functools.partial(self._wrapper, name)
            else:
                retval = []
                for drone in self._drones.values():
                    ret = getattr(drone.name)
                    if not isinstance(ret, Collection):
                        retval.append((ret,))
                    else:
                        retval.append(tuple(ret))
                return retval

        else:
            return super().__getattr__(name)

    def add_and_pair(self: Swarm, *drones: tuple[str, Drone]):
        """
        Description
            Adds the passed drone object(s) to the swarm and pairs them.

        Arguments
            *drones:
                port name and Drone instance sets.

        Example
            add_and_pair("/dev/ttyACM0", Drone(), "/dev/ttyACM1", Drone())
        """
        """
        説明
            渡されたドローンオブジェクトをストームに追加し、それらをペアリングする。

        引数
            *drones:
                ポート名とドローンインスタンスの組み合わせ。

        例
            add_and_pair("/dev/ttyACM0", Drone(), "/dev/ttyACM1", Drone())
        """
        i = 0
        while i < len(drones):
            port, drone = drones[i : i + 2]
            drone.pair(port)
            self._drones[port] = drone
            i = i + 2

    def remove(self: Swarm, *drones: tuple[str | Drone]):
        # Removes the drone from the swarm. It is the user's responsibility to land and close the drone.
        # スウォームからドローンを削除する。ドローンを着陸させて閉じるのはユーザーの責任。
        if isinstance(drones[0], str):
            self._drones = {
                port: swarm_drone
                for port, swarm_drone in self._drones.items()
                if port not in drones
            }
        else:
            self._drones = {
                port: swarm_drone
                for port, swarm_drone in self._drones.items()
                if swarm_drone not in drones
            }

    async def takeoff(self: Swarm, *drones: tuple[str | Drone]) -> None:
        await asyncio.gather(
            *[_async_takeoff(drone) for drone in self._drones.values()]
        )

    async def land(self: Swarm) -> None:
        await asyncio.gather(*[_async_land(drone) for drone in self._drones.values()])

    async def spiral(self, speed=50, seconds=5, direction=1):
        power = int(speed)
        self.sendControl(0, power, 100 * -direction, -power)
        await asyncio.sleep(seconds)
