"""Extract Menu Info gecko payload layout and parsing (crowd-control fork).

Mirrors gecko/ExtractMenuInfo/SendMenuFrame.asm. Base EXI transfer length is
0x54 (command byte at 0x0 plus payload bytes 0x1–0x53). Offline CSS CPU fields:

- 0x41–0x44: CPU level bytes (CSSData->players[i].cpu_level +0x0F)
- 0x45–0x48: CSSDoor.is_hold_cpu_slider (+0x12) at mnCharSel_803F0DFC.doors[i]
- 0x4C–0x52: live match pause bytes (when this fork's payload is active)
- 0x53: payload discriminator (0 = normal, 1 = pause-open, 2 = pause-close)
- 0x54+: counted crowd-control tail for normal payloads. NB1 tails contain
  optional debug watches followed by four per-port neutral-B charge counters.

See doldecomp/melee src/melee/mn/types.h (PlayerInitData, CSSDoor).
Watch values are exposed on ``gamestate.custom["gecko_watch_values"]``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from melee import enums

if TYPE_CHECKING:
    from melee.gamestate import GameState, PlayerState

EXI_TRANSFER_LEN = 0x54
"""Base bytes sent by SendMenuFrame through the payload discriminator."""
PAYLOAD_KIND_OFFSET = 0x53
PAYLOAD_KIND_NORMAL = 0
PAYLOAD_KIND_PAUSE_OPEN = 1
PAYLOAD_KIND_PAUSE_CLOSE = 2
PAYLOAD_KIND_CUSTOM_KEY = "gecko_payload_kind"
WATCH_PAYLOAD_COUNT_OFFSET = 0x54
WATCH_PAYLOAD_VALUES_OFFSET = 0x58
WATCH_PAYLOAD_VALUE_SIZE = 4
NEUTRAL_B_CHARGE_SIGNATURE = b"NB1"
NEUTRAL_B_CHARGE_SIGNATURE_OFFSET = 0x55
NEUTRAL_B_CHARGE_VALUE_COUNT = 4
NEUTRAL_B_CHARGE_CUSTOM_KEY = "gecko_neutral_b_charges"
NEUTRAL_B_CHARGE_CHARACTERS = frozenset(
    {
        enums.Character.DK,
        enums.Character.SHEIK,
        enums.Character.SAMUS,
        enums.Character.MEWTWO,
    }
)

# Scene halfwords (offset 0x1, big-endian u16).
SCENE_PRESS_START = 0x0000
SCENE_MAIN_MENU = 0x0001
SCENE_OFFLINE_CSS = 0x0002
SCENE_SLIPPI_ONLINE_CSS = 0x0008
SCENE_OFFLINE_SSS = 0x0102
SCENE_ONLINE_SSS = 0x0108
SCENE_IN_GAME = 0x0202
SCENE_ONLINE_IN_GAME = 0x0208
SCENE_SUDDEN_DEATH = 0x0302
SCENE_POSTGAME = 0x0402

MATCH_PAUSE_MIN_LEN = 0x53
"""Minimum payload length to read pause bytes through offset 0x52."""


def payload_kind(event_bytes: bytes) -> int:
    if len(event_bytes) <= PAYLOAD_KIND_OFFSET:
        return PAYLOAD_KIND_NORMAL
    return _read_u8(event_bytes, PAYLOAD_KIND_OFFSET)

def scene_to_menu_state(scene: int) -> enums.Menu:
    if scene == SCENE_OFFLINE_CSS:
        return enums.Menu.CHARACTER_SELECT
    if scene in (SCENE_OFFLINE_SSS, SCENE_ONLINE_SSS):
        return enums.Menu.STAGE_SELECT
    if scene == SCENE_IN_GAME:
        return enums.Menu.IN_GAME
    if scene == SCENE_SUDDEN_DEATH:
        return enums.Menu.SUDDEN_DEATH
    if scene == SCENE_POSTGAME:
        return enums.Menu.POSTGAME_SCORES
    if scene == SCENE_MAIN_MENU:
        return enums.Menu.MAIN_MENU
    if scene == SCENE_SLIPPI_ONLINE_CSS:
        return enums.Menu.SLIPPI_ONLINE_CSS
    if scene == SCENE_PRESS_START:
        return enums.Menu.PRESS_START
    return enums.Menu.UNKNOWN_MENU


def scene_to_game_mode(scene: int) -> enums.GameMode:
    try:
        return enums.GameMode(scene & 0xFF)
    except ValueError:
        return enums.GameMode.UNKNOWN_GAME_MODE


def menu_state_needs_css_players(menu_state: enums.Menu) -> bool:
    return menu_state in (
        enums.Menu.CHARACTER_SELECT,
        enums.Menu.SLIPPI_ONLINE_CSS,
        enums.Menu.STAGE_SELECT,
    )


def _read_u8(event_bytes: bytes, offset: int) -> int:
    return int(np.ndarray((1,), ">B", event_bytes, offset)[0])


def _read_u16(event_bytes: bytes, offset: int) -> int:
    return int(np.ndarray((1,), ">H", event_bytes, offset)[0])


def _read_i32(event_bytes: bytes, offset: int) -> int:
    return int(np.ndarray((1,), ">i", event_bytes, offset)[0])


def _read_u32(event_bytes: bytes, offset: int) -> int:
    return int(np.ndarray((1,), ">I", event_bytes, offset)[0])


def _read_f32(event_bytes: bytes, offset: int) -> float:
    return float(np.ndarray((1,), ">f", event_bytes, offset)[0])


def _fresh_player_states() -> dict[int, PlayerState]:
    from melee.gamestate import PlayerState

    return {
        1: PlayerState(),
        2: PlayerState(),
        3: PlayerState(),
        4: PlayerState(),
    }


def apply_extract_menu_info_payload(event_bytes: bytes, gamestate: GameState) -> None:
    """Update *gamestate* from a SendMenuFrame EXI buffer."""
    scene = _read_u16(event_bytes, 0x1)
    kind = payload_kind(event_bytes)
    latched_kind = gamestate.custom.get(PAYLOAD_KIND_CUSTOM_KEY)
    if kind in (PAYLOAD_KIND_PAUSE_OPEN, PAYLOAD_KIND_PAUSE_CLOSE) or latched_kind not in (
        PAYLOAD_KIND_PAUSE_OPEN,
        PAYLOAD_KIND_PAUSE_CLOSE,
    ):
        gamestate.custom[PAYLOAD_KIND_CUSTOM_KEY] = kind
    gamestate.menu_scene = scene
    gamestate.game_mode = scene_to_game_mode(scene)
    menu_state = scene_to_menu_state(scene)
    gamestate.menu_state = menu_state

    if menu_state_needs_css_players(menu_state):
        gamestate.players = _fresh_player_states()

    if menu_state in (enums.Menu.CHARACTER_SELECT, enums.Menu.SLIPPI_ONLINE_CSS):
        _apply_css_screen_fields(event_bytes, gamestate)

    if menu_state == enums.Menu.STAGE_SELECT:
        _apply_stage_select_fields(event_bytes, gamestate, scene)

    gamestate.frame = _read_i32(event_bytes, 0x39)

    try:
        gamestate.submenu = enums.SubMenu(_read_u8(event_bytes, 0x3D))
    except (TypeError, ValueError):
        gamestate.submenu = enums.SubMenu.UNKNOWN_SUBMENU

    try:
        gamestate.menu_selection = _read_u8(event_bytes, 0x3E)
    except TypeError:
        gamestate.menu_selection = 0

    _apply_match_pause_fields(event_bytes, gamestate)
    if kind in (PAYLOAD_KIND_PAUSE_OPEN, PAYLOAD_KIND_PAUSE_CLOSE):
        return

    _apply_costume_fields(event_bytes, gamestate)
    _apply_online_nametag_submenu(event_bytes, gamestate)
    _apply_cpu_level_fields(event_bytes, gamestate)
    _apply_cpu_slider_fields(event_bytes, gamestate)
    _apply_watch_payload_fields(event_bytes, gamestate)


def _apply_css_screen_fields(event_bytes: bytes, gamestate: GameState) -> None:
    for port, (x_off, y_off) in enumerate(
        ((0x3, 0x7), (0xB, 0xF), (0x13, 0x17), (0x1B, 0x1F)),
        start=1,
    ):
        player = gamestate.players[port]
        player.controller_status = enums.ControllerStatus(_read_u8(event_bytes, 0x24 + port))
        player.cursor.x = np.float32(_read_f32(event_bytes, x_off))
        player.cursor.y = np.float32(_read_f32(event_bytes, y_off))
        try:
            character = enums.to_internal(_read_u8(event_bytes, 0x28 + port))
            player.character = character
            player.character_selected = character
        except TypeError:
            player.character = enums.Character.UNKNOWN_CHARACTER
            player.character_selected = enums.Character.UNKNOWN_CHARACTER
        try:
            player.coin_down = _read_u8(event_bytes, 0x2C + port) == 2
        except TypeError:
            player.coin_down = False

    gamestate.ready_to_start = _read_u8(event_bytes, 0x23)


def _apply_stage_select_fields(
    event_bytes: bytes,
    gamestate: GameState,
    scene: int,
) -> None:
    try:
        gamestate.stage = enums.Stage(_read_u8(event_bytes, 0x24))
    except ValueError:
        gamestate.stage = enums.Stage.NO_STAGE

    # gecko/ExtractMenuInfo fills cursors only on offline SSS (0x0102).
    if scene != SCENE_OFFLINE_SSS:
        return

    cursor_x = np.float32(_read_f32(event_bytes, 0x31))
    cursor_y = np.float32(_read_f32(event_bytes, 0x35))
    for player in gamestate.players.values():
        player.cursor.x = cursor_x
        player.cursor.y = cursor_y


def _apply_costume_fields(event_bytes: bytes, gamestate: GameState) -> None:
    try:
        if gamestate.menu_state == enums.Menu.SLIPPI_ONLINE_CSS:
            gamestate.players[1].costume = _read_u8(event_bytes, 0x3F)
            return
        if gamestate.menu_state == enums.Menu.CHARACTER_SELECT:
            for port, offset in ((1, 0x3F), (2, 0x49), (3, 0x4A), (4, 0x4B)):
                if len(event_bytes) <= offset:
                    continue
                gamestate.players[port].costume = _read_u8(event_bytes, offset)
    except (TypeError, KeyError):
        pass


def _apply_online_nametag_submenu(event_bytes: bytes, gamestate: GameState) -> None:
    if gamestate.menu_state != enums.Menu.SLIPPI_ONLINE_CSS:
        return
    try:
        nametag = _read_u8(event_bytes, 0x40)
        if nametag == 0x05:
            gamestate.submenu = enums.SubMenu.NAME_ENTRY_SUBMENU
        elif nametag == 0x00:
            gamestate.submenu = enums.SubMenu.ONLINE_CSS
    except TypeError:
        pass


def _apply_cpu_level_fields(event_bytes: bytes, gamestate: GameState) -> None:
    """Parse CPU level bytes at 0x41–0x44 (PlayerInitData.cpu_level via gecko)."""
    if gamestate.menu_state != enums.Menu.CHARACTER_SELECT:
        return
    try:
        for port in range(1, 5):
            cpu_level = _read_u8(event_bytes, 0x40 + port)
            if (
                gamestate.players[port].controller_status
                != enums.ControllerStatus.CONTROLLER_CPU
            ):
                cpu_level = 0
            gamestate.players[port].cpu_level = cpu_level
    except (TypeError, KeyError):
        pass


def _apply_cpu_slider_fields(event_bytes: bytes, gamestate: GameState) -> None:
    """Parse slider-held bytes at 0x45–0x48 (CSSDoor.is_hold_cpu_slider via gecko)."""
    if gamestate.menu_state != enums.Menu.CHARACTER_SELECT:
        return
    try:
        for port in range(1, 5):
            holding = _read_u8(event_bytes, 0x44 + port)
            if (
                gamestate.players[port].controller_status
                != enums.ControllerStatus.CONTROLLER_CPU
            ):
                holding = 0
            gamestate.players[port].is_holding_cpu_slider = bool(holding)
    except (TypeError, KeyError):
        pass


def _apply_match_pause_fields(event_bytes: bytes, gamestate: GameState) -> None:
    if len(event_bytes) < MATCH_PAUSE_MIN_LEN:
        return
    kind = payload_kind(event_bytes)
    try:
        pause_slot = _read_u8(event_bytes, 0x4C)
        pauser = int(np.ndarray((1,), ">b", event_bytes, 0x4D)[0])
        pause_timer = _read_u8(event_bytes, 0x4E)
        pause_cooldown = _read_u8(event_bytes, 0x4F)
        hud_enabled = _read_u8(event_bytes, 0x50) != 0
        match_over = _read_u8(event_bytes, 0x51) != 0
        match_end_pending = _read_u8(event_bytes, 0x52) != 0
    except TypeError:
        return

    pause = gamestate.match_pause
    pause.raw_pause_slot = pause_slot
    pause.pauser_port_index = pauser
    pause.pause_open_event = pause.pause_open_event or kind == PAYLOAD_KIND_PAUSE_OPEN
    pause.pause_close_event = pause.pause_close_event or kind == PAYLOAD_KIND_PAUSE_CLOSE
    if kind == PAYLOAD_KIND_PAUSE_CLOSE:
        pause.pause_open_event = False
    pause.pause_timer_frames = pause_timer
    pause.pause_cooldown_frames = pause_cooldown
    pause.hud_enabled = hud_enabled
    pause.match_over = match_over
    pause.match_end_pending = match_end_pending


def _apply_watch_payload_fields(event_bytes: bytes, gamestate: GameState) -> None:
    if len(event_bytes) <= WATCH_PAYLOAD_COUNT_OFFSET:
        return
    count = _read_u8(event_bytes, WATCH_PAYLOAD_COUNT_OFFSET)
    values_end = WATCH_PAYLOAD_VALUES_OFFSET + (count * WATCH_PAYLOAD_VALUE_SIZE)
    if count == 0 or len(event_bytes) < values_end:
        return
    values = tuple(
        _read_u32(event_bytes, WATCH_PAYLOAD_VALUES_OFFSET + (index * WATCH_PAYLOAD_VALUE_SIZE))
        for index in range(count)
    )
    has_charge_extension = (
        count >= NEUTRAL_B_CHARGE_VALUE_COUNT
        and event_bytes[
            NEUTRAL_B_CHARGE_SIGNATURE_OFFSET:
            NEUTRAL_B_CHARGE_SIGNATURE_OFFSET + len(NEUTRAL_B_CHARGE_SIGNATURE)
        ]
        == NEUTRAL_B_CHARGE_SIGNATURE
    )
    if not has_charge_extension:
        gamestate.custom["gecko_watch_values"] = values
        return

    debug_count = count - NEUTRAL_B_CHARGE_VALUE_COUNT
    gamestate.custom["gecko_watch_values"] = values[:debug_count]
    charges = values[debug_count:]
    gamestate.custom[NEUTRAL_B_CHARGE_CUSTOM_KEY] = charges
    for port, player_state in gamestate.players.items():
        if 1 <= port <= len(charges) and player_state.character in NEUTRAL_B_CHARGE_CHARACTERS:
            player_state.neutral_b_charge = charges[port - 1]


def apply_neutral_b_charge(player_state: PlayerState, port: int, gamestate: GameState) -> None:
    """Apply a signature-validated per-port charge value to a supported fighter."""
    charges = gamestate.custom.get(NEUTRAL_B_CHARGE_CUSTOM_KEY)
    if (
        isinstance(charges, tuple)
        and 1 <= port <= len(charges)
        and player_state.character in NEUTRAL_B_CHARGE_CHARACTERS
    ):
        charge = charges[port - 1]
        if isinstance(charge, int):
            player_state.neutral_b_charge = charge
