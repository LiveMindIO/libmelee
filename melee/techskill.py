"""Helper functions for with some techskill examples"""

from melee import enums


def multishine(ai_state, controller):
    """Frame-perfect multishines as Fox or Falco."""
    # If standing, shine
    if ai_state.action == enums.Action.STANDING:
        controller.press_button(enums.Button.BUTTON_B)
        controller.tilt_analog(enums.Button.BUTTON_MAIN, 0.5, 0)
        return

    # Shine on the character's final knee-bend frame, else nothing.
    if ai_state.action == enums.Action.KNEE_BEND:
        jump_squat_frame = 5 if ai_state.character == enums.Character.FALCO else 3
        if ai_state.action_frame == jump_squat_frame:
            controller.press_button(enums.Button.BUTTON_B)
            controller.tilt_analog(enums.Button.BUTTON_MAIN, 0.5, 0)
            return
        controller.release_all()
        return

    shine_start = ai_state.action == enums.Action.DOWN_B_STUN or ai_state.action == enums.Action.DOWN_B_GROUND_START

    # Jump out of shine
    if shine_start and ai_state.action_frame >= 4 and ai_state.on_ground:
        controller.press_button(enums.Button.BUTTON_Y)
        return

    if ai_state.action == enums.Action.DOWN_B_GROUND:
        controller.press_button(enums.Button.BUTTON_Y)
        return

    controller.release_all()


def upsmashes(ai_state, controller):
    """Spam upsmashes"""
    if ai_state.action == enums.Action.STANDING:
        controller.tilt_analog(enums.Button.BUTTON_C, 0.5, 1)
        return

    controller.release_all()
