Public API
----------

Bot API
~~~~~~~

``CharacterState.can_jump()`` and ``melee.bot.can_jump()`` include the late
interruptible frames of common ``Action.LANDING`` using each character's NTSC
1.02 normal landing lag. Special and aerial-attack landing lag are not
jumpable through these APIs.

.. automodule:: melee.bot
   :members:
   :imported-members:
   :undoc-members:

Framedata Query API
~~~~~~~~~~~~~~~~~~~

.. automodule:: melee.bot.framedata_query
   :members:
   :undoc-members:

Master Hand
~~~~~~~~~~~

.. automodule:: melee.master_hand
   :members:
   :undoc-members:

Slippstream
~~~~~~~~~~~

.. automodule:: melee.slippstream
   :members:
   :undoc-members:

SLP File Streaming
~~~~~~~~~~~~~~~~~~

.. automodule:: melee.slpfilestreamer
   :members:
   :undoc-members:
