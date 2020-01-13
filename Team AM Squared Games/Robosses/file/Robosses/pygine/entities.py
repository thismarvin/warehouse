from enum import IntEnum
import math
import random
from pygame import Rect
from pygine.base import PygineObject
from pygine.draw import draw_rectangle
from pygine.geometry import Rectangle, Circle
from pygine import globals
from pygine.input import InputType, pressed, pressing
from pygine.maths import Vector2
from pygine.resource import Sprite, SpriteType
from pygine.sounds import play_sound
from pygine.utilities import CameraType, Color, Timer
from random import randint


class Entity(PygineObject):
    def __init__(self, x=0, y=0, width=1, height=1):
        super(Entity, self).__init__(x, y, width, height)
        self.color = Color.WHITE
        self.layer = 0
        self.remove = False
        self.__bounds_that_actually_draw_correctly = Rectangle(
            self.x, self.y, self.width, self.height, self.color, 2)

    def set_color(self, color):
        self.color = color
        self.__bounds_that_actually_draw_correctly.color = color

    def set_location(self, x, y):
        super(Entity, self).set_location(x, y)
        self.__bounds_that_actually_draw_correctly.set_location(self.x, self.y)

    def update(self, delta_time, scene_data):
        raise NotImplementedError(
            "A class that inherits Entity did not implement the update(delta_time, scene_data) method")

    def _draw_bounds(self, surface, camera_type):
        self.__bounds_that_actually_draw_correctly.draw(surface, camera_type)

    def draw(self, surface):
        raise NotImplementedError(
            "A class that inherits Entity did not implement the draw(surface) method")


class Direction(IntEnum):
    NONE = 0,
    UP = 1,
    DOWN = 2,
    LEFT = 3,
    RIGHT = 4


class Kinetic(Entity):
    def __init__(self, x, y, width, height, speed):
        super(Kinetic, self).__init__(x, y, width, height)
        self.velocity = Vector2()
        self.acceleration = Vector2()
        self.default_move_speed = speed
        self.move_speed = speed
        self.facing = Direction.NONE
        self.collision_rectangles = []
        self.collision_width = 0

        self.target = 1.0 / 60
        self.accumulator = 0

    def _update_collision_rectangles(self):
        self.collision_width = 4
        self.collision_rectangles = [
            Rect(self.x + self.collision_width, self.y - self.collision_width,
                 self.width - self.collision_width * 2, self.collision_width),
            Rect(self.x + self.collision_width, self.y + self.height, self.width -
                 self.collision_width * 2, self.collision_width),
            Rect(self.x - self.collision_width, self.y + self.collision_width,
                 self.collision_width, self.height - self.collision_width * 2),
            Rect(self.x + self.width, self.y + self.collision_width,
                 self.collision_width, self.height - self.collision_width * 2)
        ]

    def _calculate_scaled_speed(self, delta_time):
        self.move_speed = self.default_move_speed * delta_time

    def _apply_force(self, delta_time):
        # Semi-Implict Euler Integrator
        self.velocity = Vector2(
            self.velocity.x + self.acceleration.x * delta_time,
            self.velocity.y + self.acceleration.y * delta_time
        )
        self.set_location(
            self.x + self.velocity.x * delta_time,
            self.y + self.velocity.y * delta_time
        )

    def _simulate(self, elapsed_time, scene_data):
        self.accumulator += elapsed_time

        while(self.accumulator >= self.target):
            self._apply_force(self.target)
            self._collision(scene_data)

            self.accumulator -= self.target

    def _collision(self, scene_data):
        raise NotImplementedError(
            "A class that inherits Kinetic did not implement the _collision(entities, entity_quad_tree) method")

    def update(self, delta_time, scene_data):
        self._simulate(delta_time, scene_data)

    def _draw_collision_rectangles(self, surface):
        for r in self.collision_rectangles:
            draw_rectangle(
                surface,
                r,
                CameraType.DYNAMIC,
                Color.RED,
            )


class Actor(Kinetic):
    def __init__(self, x, y, width, height, speed):
        super(Actor, self).__init__(x, y, width, height, speed)

    def _update_input(self):
        raise NotImplementedError(
            "A class that inherits Actor did not implement the _update_input() method")


class Gun(Entity):
    def __init__(self, x, y):
        super(Gun, self).__init__(x, y, 32, 16)
        self.sprite = Sprite(self.x, self.y, SpriteType.NONE)
        self.facing = Direction.LEFT

        self.bullet_travel = 16 * 7
        self.bullet_speed = 300
        self.bullet_damage = 10

        self.timer_frequency = Timer(250)
        self.can_shoot = True

    def face(self, direction):
        self.facing = direction

        if (self.facing == Direction.UP):
            self.sprite.set_sprite(SpriteType.GUN_0_V)
        else:
            self.sprite.set_sprite(SpriteType.GUN_0_H)

        if (self.facing == Direction.RIGHT):
            self.sprite.flip_horizontally(True)
        elif (self.facing == Direction.LEFT):
            self.sprite.flip_horizontally(False)

    def fire(self, x, y, extra_velocity, scene_data):
        if (not self.can_shoot):
            return

        extra = 0
        direction = 0

        if (self.facing == Direction.LEFT or self.facing == Direction.RIGHT):
            if (self.facing == Direction.LEFT):
                direction = -1
                if (extra_velocity < 0):
                    extra = extra_velocity
            else:
                direction = 1
                if (extra_velocity > 0):
                    extra = extra_velocity

            # Create Bullet
            scene_data.entity_buffer.append(
                Bullet(
                    x, y,
                    Vector2(direction * self.bullet_speed + extra, 0),
                    self.bullet_travel,
                    self.bullet_damage
                )
            )
        else:
            direction = -1
            if (extra_velocity < 0):
                extra = extra_velocity

            # Create Bullet
            scene_data.entity_buffer.append(
                Bullet(
                    x, y,
                    Vector2(0, direction * self.bullet_speed + extra),
                    self.bullet_travel,
                    self.bullet_damage
                )
            )

        self.can_shoot = False
        self.timer_frequency.reset()
        self.timer_frequency.start()

        play_sound("shoot.wav", 0.15)

    def set_location(self, x, y):
        super(Gun, self).set_location(x, y)
        self.sprite.set_location(self.x, self.y)

    def update(self, delta_time, scene_data):
        self.timer_frequency.update(delta_time)
        if (self.timer_frequency.done):
            self.can_shoot = True

    def draw(self, surface):
        self.sprite.draw(surface, CameraType.STATIC)


class Bullet(Kinetic):
    def __init__(self, x, y, velocity, travel, damage):
        super(Bullet, self).__init__(x, y, 16, 16, 0)
        self.sprite = Sprite(self.x, self.y, SpriteType.BULLET)
        self.velocity = velocity

        self.travel = travel
        self.damage = damage

        self.starting_x = x
        self.starting_y = y

    def set_location(self, x, y):
        super(Bullet, self).set_location(x, y)
        self.sprite.set_location(self.x, self.y)

    def _collision(self, scene_data):
        if (self.x + self.width < 0 or self.x > scene_data.scene_bounds.width):
            self.remove = True

    def update(self, delta_time, scene_data):

        if (abs(self.x - self.starting_x) > self.travel or abs(self.y - self.starting_y) > self.travel):
            self.remove = True

        super(Bullet, self).update(delta_time, scene_data)

    def draw(self, surface):
        if (globals.debugging):
            draw_rectangle(
                surface,
                self.bounds,
                CameraType.DYNAMIC,
                self.color
            )
        else:
            self.sprite.draw(surface, CameraType.STATIC)


class BasicGun(Gun):
    def __init__(self, x, y):
        super(BasicGun, self).__init__(x, y)

        self.timer_frequency = Timer(150)

        self.sprite.set_sprite(SpriteType.GUN_0_H)

    def update(self, delta_time, scene_data):
        super(BasicGun, self).update(delta_time, scene_data)

    def draw(self, surface):
        super(BasicGun, self).draw(surface)


class WhatGun(Gun):
    def __init__(self, x, y):
        super(WhatGun, self).__init__(x, y)

        self.timer_frequency = Timer(100)
        self.bullet_damage = 11

        self.sprite.set_sprite(SpriteType.GUN_1_H)

    def update(self, delta_time, scene_data):
        super(WhatGun, self).update(delta_time, scene_data)

    def draw(self, surface):
        super(WhatGun, self).draw(surface)


class Player(Actor):
    def __init__(self, x, y):
        super(Player, self).__init__(x, y, 16, 32, 90)
        self.sprite = Sprite(self.x, self.y, SpriteType.NONE)
        self.query_result = None

        self.jump_height = 16 * 5 + 4
        self.jump_duration = 0.5

        self.gravity = 2 * self.jump_height / \
            (self.jump_duration * self.jump_duration)

        self.initial_jump_velocity = self.gravity * self.jump_duration

        self.lateral_acceleration = 175
        self.friction = 150
        self.drag = 50

        self.velocity = Vector2(0, 0)
        self.acceleration = Vector2(0, self.gravity)

        self.grounded = False
        self.jumping = False

        self.sprite_flipped = False

        self.total_health = 3
        self.health = self.total_health
        self.dead = False

        self.flashes = 4
        self.invinsible_duration = 1600
        self.timer_invinsible = Timer(self.invinsible_duration)
        self.timer_flash = Timer(self.invinsible_duration / (self.flashes * 2))
        self.damaged = False
        self.flashing = False

        self.entered_arena = False

        self.area = Rect(
            self.x - 8,
            self.y - 8,
            self.width + 8 * 2,
            self.height + 8 * 2
        )

    def reset(self):
        self.velocity = Vector2(0, 0)
        self.acceleration = Vector2(0, self.gravity)

        self.grounded = False
        self.jumping = False

        self.health = self.total_health
        self.dead = False
        self.damaged = False
        self.flashing = False

        self.entered_arena = False

    def take_damage(self):
        if (self.damaged):
            return

        self.damaged = True
        self.health -= 1

        if (self.health <= 0):
            self.dead = True
            self.velocity.y = -self.initial_jump_velocity * 0.6
            play_sound("robot_dead.wav", 0.25)
        else:
            self.timer_invinsible.start()
            self.timer_flash.start()
            play_sound("robot_hurt.wav", 1)

    def enter_arena(self):
        self.entered_arena = True

    def __update_health(self, delta_time):
        if (not self.damaged or self.dead):
            return

        self.timer_invinsible.update(delta_time)
        self.timer_flash.update(delta_time)

        if (self.timer_flash.done):
            self.flashing = not self.flashing
            self.timer_flash.reset()
            self.timer_flash.start()

        if (self.timer_invinsible.done):
            self.damaged = False
            self.flashing = False
            self.timer_invinsible.reset()

    def _update_input(self):
        if (self.dead):
            return

        if (pressing(InputType.LEFT) and not pressing(InputType.RIGHT)):
            self.acceleration.x = -self.lateral_acceleration

            if (self.sprite_flipped):
                self.sprite.flip_horizontally(True)
                self.sprite_flipped = False

        if (pressing(InputType.RIGHT) and not pressing(InputType.LEFT)):
            self.acceleration.x = self.lateral_acceleration

            if (not self.sprite_flipped):
                self.sprite.flip_horizontally(True)
                self.sprite_flipped = True

        if (not pressing(InputType.LEFT) and not pressing(InputType.RIGHT)):
            if (self.velocity.x != 0):
                dir = -1 if self.velocity.x > 0 else 1
                if (self.grounded):
                    self.acceleration.x = self.friction * dir
                else:
                    self.acceleration.x = self.drag * dir

            if (-1 < self.velocity.x and self.velocity.x < 1):
                self.velocity.x = 0
                self.acceleration.x = 0

        if (self.grounded and not self.jumping and pressing(InputType.A)):
            self.velocity.y = -self.initial_jump_velocity
            self.jumping = True
            play_sound("jump.wav", 0.5)

        if (self.jumping and self.velocity.y < -self.initial_jump_velocity / 2 and not pressing(InputType.A)):
            self.velocity.y = -self.initial_jump_velocity / 2
            self.jumping = False

        if (self.velocity.x < -self.move_speed):
            self.velocity.x = -self.move_speed

        if (self.velocity.x > self.move_speed):
            self.velocity.x = self.move_speed

    def __rectanlge_collision_logic(self, entity):
        # Bottom
        if self.collision_rectangles[0].colliderect(entity.bounds) and self.velocity.y < 0:
            self.set_location(self.x, entity.bounds.bottom)
        # Top
        if self.collision_rectangles[1].colliderect(entity.bounds) and self.velocity.y > 0:
            self.set_location(self.x, entity.bounds.top - self.bounds.height)

            self.velocity.y = 0
            self.grounded = True
            self.jumping = False

        # Right
        if self.collision_rectangles[2].colliderect(entity.bounds) and self.velocity.x < 0:
            self.set_location(entity.bounds.right, self.y)
        # Left
        if self.collision_rectangles[3].colliderect(entity.bounds) and self.velocity.x > 0:
            self.set_location(entity.bounds.left - self.bounds.width, self.y)

    def _collision(self, scene_data):
        self._update_collision_rectangles()

        if (self.dead):
            return

        if (globals.debugging):
            for e in scene_data.entities:
                e.set_color(Color.WHITE)

        self.area = Rect(
            self.x - 16,
            self.y - 16,
            self.width + 16 * 2,
            self.height + 16 * 2
        )

        self.query_result = scene_data.entity_quad_tree.query(self.area)

        self.grounded = False

        if (self.x < 0):
            self.set_location(0, self.y)
            self.velocity.x = -self.velocity.x * 0.75

        if (self.x + self.width > scene_data.scene_bounds.width):
            self.set_location(
                scene_data.scene_bounds.width - self.width, self.y)
            self.velocity.x = -self.velocity.x * 0.75

        for e in self.query_result:
            if e is self:
                continue

            if (globals.debugging):
                e.set_color(Color.RED)

            if isinstance(e, Block):
                self.__rectanlge_collision_logic(e)
                self._update_collision_rectangles()

    def update(self, delta_time, scene_data):
        if (not self.entered_arena):
            return

        self._update_input()
        self.__update_health(delta_time)

        super(Player, self).update(delta_time, scene_data)

    def draw(self, surface):
        if globals.debugging:
            self._draw_collision_rectangles(surface)
            draw_rectangle(
                surface,
                self.bounds,
                CameraType.DYNAMIC,
                self.color
            )
            draw_rectangle(
                surface,
                self.area,
                CameraType.DYNAMIC,
                Color.BLACK,
                1
            )
        else:
            if (not self.flashing):
                self.sprite.draw(surface, CameraType.DYNAMIC)


class PlayerA(Player):
    def __init__(self, x, y):
        super(PlayerA, self).__init__(x, y)
        self.sprite = Sprite(self.x - 9, self.y - 16, SpriteType.PLAYERA)
        # Character specific stuff here.
        self.gun = BasicGun(self.x - 24, self.y + 8)
        self.shooting_up = False

    def set_location(self, x, y):
        super(PlayerA, self).set_location(x, y)
        self.sprite.set_location(self.x - 9, self.y - 16)

        if (not self.shooting_up):
            # Facing Left
            if (not self.sprite_flipped):
                self.gun.set_location(self.x - 24, self.y + 8)
                self.gun.face(Direction.LEFT)
            else:
                self.gun.set_location(self.x + self.width - 4, self.y + 8)
                self.gun.face(Direction.RIGHT)
        else:
            # Facing Left
            if (not self.sprite_flipped):
                self.gun.set_location(self.x - 14, self.y - 5)
            else:
                self.gun.set_location(self.x + 9, self.y - 5)

            self.gun.face(Direction.UP)

    def __blast_em_logic(self, scene_data):

        self.shooting_up = False

        if (pressing(InputType.UP)):
            if (pressing(InputType.X)):
                self.shooting_up = True

                if (not self.sprite_flipped):
                    self.gun.fire(
                        self.x - 12,
                        self.y - 16,
                        self.velocity.y,
                        scene_data
                    )
                else:
                    self.gun.fire(
                        self.x + 10,
                        self.y - 16,
                        self.velocity.y,
                        scene_data
                    )
        else:
            if (pressing(InputType.X)):
                if (not self.sprite_flipped):
                    self.gun.fire(
                        self.x - 24, self.y + 9,
                        self.velocity.x,
                        scene_data
                    )
                else:
                    self.gun.fire(
                        self.x + self.width + 4,
                        self.y + 9,
                        self.velocity.x,
                        scene_data)

    def update(self, delta_time, scene_data):
        if (not self.entered_arena):
            return

        self.__blast_em_logic(scene_data)

        self.gun.update(delta_time, scene_data)
        super(PlayerA, self).update(delta_time, scene_data)

    def draw(self, surface):
        super(PlayerA, self).draw(surface)

        if (not globals.debugging):
            self.gun.draw(surface)


class PlayerB(Player):
    def __init__(self, x, y):
        super(PlayerB, self).__init__(x, y)
        self.sprite = Sprite(self.x - 9, self.y - 16, SpriteType.PLAYERB)
        # Character specific stuff here.
        self.gun = WhatGun(self.x - 24, self.y + 8)
        self.shooting_up = False

        self.jump_height = 16 * 6 + 4
        self.jump_duration = 0.5

        self.gravity = 2 * self.jump_height / \
            (self.jump_duration * self.jump_duration)

        self.initial_jump_velocity = self.gravity * self.jump_duration
        self.acceleration = Vector2(0, self.gravity)

        self.lateral_acceleration = 600
        self.friction = 30
        self.drag = 30
        self.move_speed = 300

        self.total_health = 2
        self.health = self.total_health

    def set_location(self, x, y):
        super(PlayerB, self).set_location(x, y)
        self.sprite.set_location(self.x - 9, self.y - 16)

        if (not self.shooting_up):
            # Facing Left
            if (not self.sprite_flipped):
                self.gun.set_location(self.x - 24, self.y + 8)
                self.gun.face(Direction.LEFT)
            else:
                self.gun.set_location(self.x + self.width - 4, self.y + 8)
                self.gun.face(Direction.RIGHT)
        else:
            # Facing Left
            if (not self.sprite_flipped):
                self.gun.set_location(self.x - 14, self.y - 5)
            else:
                self.gun.set_location(self.x + 9, self.y - 5)

            self.gun.face(Direction.UP)

    def __blast_em_logic(self, scene_data):

        self.shooting_up = False

        if (pressing(InputType.UP)):
            if (pressing(InputType.X)):
                self.shooting_up = True

                if (not self.sprite_flipped):
                    self.gun.fire(
                        self.x - 12,
                        self.y - 16,
                        self.velocity.y,
                        scene_data
                    )
                else:
                    self.gun.fire(
                        self.x + 10,
                        self.y - 16,
                        self.velocity.y,
                        scene_data
                    )
        else:
            if (pressing(InputType.X)):
                if (not self.sprite_flipped):
                    self.gun.fire(
                        self.x - 24, self.y + 9,
                        self.velocity.x,
                        scene_data
                    )
                else:
                    self.gun.fire(
                        self.x + self.width + 4,
                        self.y + 9,
                        self.velocity.x,
                        scene_data)

    def update(self, delta_time, scene_data):
        if (not self.entered_arena):
            return
        self.__blast_em_logic(scene_data)

        self.gun.update(delta_time, scene_data)
        super(PlayerB, self).update(delta_time, scene_data)

    def draw(self, surface):
        super(PlayerB, self).draw(surface)

        if (not globals.debugging):
            self.gun.draw(surface)


class Block(Entity):
    def __init__(self, x, y, width, height):
        super(Block, self).__init__(x, y, width, height)

    def update(self, delta_time, scene_data):
        pass

    def draw(self, surface):
        if globals.debugging:
            draw_rectangle(surface, self.bounds,
                           CameraType.DYNAMIC, self.color, 4)
        else:
            pass


class Boss(Entity):
    def __init__(self, x, y, width, height):
        super(Boss, self).__init__(x, y, width, height)
        self.total_health = 10000
        self.health = self.total_health
        self.dead = False

        self.health_bar_width = 192
        self.health_bar_position = Vector2((320 - 192) / 2, 8)
        self.health_bar = self.__update_health_bar()

        self.padding = 4
        self.health_bar_backing = Rect(
            self.health_bar_position.x - self.padding,
            self.health_bar_position.y - self.padding,
            self.health_bar_width + self.padding * 2,
            12 + self.padding * 2
        )

    def reset(self):
        self.health = self.total_health
        self.health_bar = self.__update_health_bar()
        self.dead = False

    def hit(self, damage):
        if (self.dead):
            return

        self.health -= damage
        self.health_bar = self.__update_health_bar()

        if (self.health <= 0):
            self.dead = True

    def __update_health_bar(self):
        return Rect(
            self.health_bar_position.x,
            self.health_bar_position.y,
            self.health * self.health_bar_width / self.total_health,
            12
        )

    def update(self, delta_time, scene_data):
        pass

    def draw(self, surface):
        # Draw health bar
        draw_rectangle(
            surface,
            self.health_bar_backing,
            CameraType.STATIC,
            Color.WHITE
        )
        draw_rectangle(
            surface,
            self.health_bar_backing,
            CameraType.STATIC,
            Color.BLACK,
            2
        )
        draw_rectangle(
            surface,
            self.health_bar,
            CameraType.STATIC,
            Color.RED
        )


class OctoArm(Kinetic):
    def __init__(self, boss, is_right):
        super(OctoArm, self).__init__(-128, 240 - 32 - 32, 128, 16, 0)

        self.boss = boss
        self.is_right = is_right

        self.color = Color.GRASS_GREEN
        self.sprite = Sprite(self.x, self.y - 32, SpriteType.OCTOPUS_ARM)
        if (self.is_right):
            self.set_location(320, self.y)
            self.sprite.flip_horizontally(True)

        self.attacking = False
        self.attack_stage = 0

        # Kinetic needs this
        self.query_result = None
        self.area = Rect(
            self.x - 8,
            self.y - 8,
            self.width + 8 * 2,
            self.height + 8 * 2
        )

    def set_location(self, x, y):
        super(OctoArm, self).set_location(x, y)
        if (not self.is_right):
            self.sprite.set_location(self.x, self.y - 32)
        else:
            self.sprite.set_location(self.x - 16, self.y - 32)

    def attack(self):
        if (self.attacking):
            return

        self.attacking = True
        self.attack_stage = 0

        direction = -1 if self.is_right else 1
        self.acceleration.x = 500 * direction

    def _collision(self, scene_data):
        self._update_collision_rectangles()

        if (globals.debugging):
            for e in scene_data.entities:
                e.set_color(Color.WHITE)

        self.area = Rect(
            self.x - 16,
            self.y - 16,
            self.width + 16 * 2,
            self.height + 16 * 2
        )

        if (not self.attacking):
            return

        self.query_result = scene_data.kinetic_quad_tree.query(self.area)

        for e in self.query_result:
            if e is self:
                continue

            if (globals.debugging):
                e.set_color(Color.RED)

            if isinstance(e, Bullet):
                if (self.bounds.colliderect(e.bounds)):
                    self.boss.hit(e.damage * 0.1)
                    e.remove = True

            if isinstance(e, Player):
                if (self.bounds.colliderect(e.bounds)):
                    e.take_damage()

    def __update_attack_logic(self):
        if (not self.attacking):
            return

        extend = 64
        if (self.attack_stage == 0):
            if (
                (not self.is_right and self.x + self.width > extend) or
                (self.is_right and self.x < 320 - extend)
            ):
                self.acceleration.x = 0
                self.velocity.x = 0

                direction = -1 if self.is_right else 1
                self.acceleration.x = 100 * direction
                self.acceleration.y = -750
                self.attack_stage += 1

        elif (self.attack_stage == 1):

            if (self.y < 32):
                self.acceleration.y = 0
                self.velocity.y = 0

                self.acceleration.y = 1000
                self.attack_stage += 1

        elif (self.attack_stage == 2):
            if (self.y > 240 - 32 - 32):
                self.acceleration.y = 0
                self.velocity.y = 0

                direction = 1 if self.is_right else -1
                self.acceleration.x = 300 * direction
                self.attack_stage += 1

                play_sound("smash.wav", 0.3)

        elif (self.attack_stage == 3):
            if (
                (not self.is_right and self.x + self.width < 0) or
                (self.is_right and self.x > 320)
            ):
                self.acceleration.x = 0
                self.velocity.x = 0

                self.attacking = False

    def update(self, delta_time, scene_data):
        self.__update_attack_logic()
        super(OctoArm, self).update(delta_time, scene_data)

    def draw(self, surface):
        if (globals.debugging):
            draw_rectangle(
                surface,
                self.bounds,
                CameraType.STATIC,
                self.color
            )
        else:
            self.sprite.draw(surface, CameraType.STATIC)


class OctoBlaster(Kinetic):
    def __init__(self, boss):
        super(OctoBlaster, self).__init__(-256, -256, 64, 64, 0)

        self.boss = boss

        self.color = Color.GRASS_GREEN

        self.sprite = Sprite(self.x, self.y, SpriteType.OCTOPUS_GUN)

        self.attacking = False
        self.attack_stage = 0

        self.wall = Direction.LEFT
        self.timer_seek = Timer(1500)

        self.timer_charge = Timer(500)

        self.laser = Rect(self.x, self.y, 0, 0)
        self.laser_detail = Rect(self.x, self.y, 0, 0)
        self.timer_laser = Timer(2000)

        # Kinetic needs this
        self.query_result = None
        self.area = Rect(
            self.x - 8,
            self.y - 8,
            self.width + 8 * 2,
            self.height + 8 * 2
        )

    def set_location(self, x, y):
        super(OctoBlaster, self).set_location(x, y)

        if (self.wall == Direction.RIGHT):
            self.sprite.set_location(self.x - 32, self.y)
        elif (self.wall == Direction.LEFT):
            self.sprite.set_location(self.x, self.y)

    def attack(self):
        if (self.attacking):
            return

        self.attacking = True
        self.attack_stage = 0

        side = randint(0, 1)
        if (side == 3):
            self.wall = Direction.UP

        elif (side == 0):
            self.wall = Direction.RIGHT
            self.set_location(
                320 + 128,
                randint(16, 240 - 80)
            )
            self.sprite.set_sprite(SpriteType.OCTOPUS_GUN)
            self.sprite.flip_horizontally(True)
            self.acceleration.x = -175

        elif (side == 1):
            self.wall = Direction.LEFT
            self.set_location(
                -128,
                randint(16, 240 - 96)
            )
            self.sprite.set_sprite(SpriteType.OCTOPUS_GUN)
            self.acceleration.x = 175

        self.timer_seek.start()

    def _collision(self, scene_data):
        self._update_collision_rectangles()

        if (globals.debugging):
            for e in scene_data.entities:
                e.set_color(Color.WHITE)

        self.area = Rect(
            self.x - 16,
            self.y - 16,
            self.width + 16 * 2,
            self.height + 16 * 2
        )

        if (not self.attacking):
            return

        self.query_result = scene_data.kinetic_quad_tree.query(self.area)

        for e in self.query_result:
            if e is self:
                continue

            if (globals.debugging):
                e.set_color(Color.RED)

            if isinstance(e, Bullet):
                if (self.bounds.colliderect(e.bounds)):
                    self.boss.hit(e.damage * 0.1)
                    e.remove = True

        if (self.attack_stage == 3):
            if (self.laser.colliderect(scene_data.actor.bounds)):
                scene_data.actor.take_damage()

    def __update_laser(self):
        if (self.wall == Direction.LEFT):
            self.laser = Rect(
                self.x + 72, self.y + 6,
                320 * 0.5, self.height
            )
            self.laser_detail = Rect(
                self.x + 72, self.y + 6 + 8,
                320 * 0.5, 48
            )
        elif (self.wall == Direction.RIGHT):
            self.laser = Rect(
                self.x - 320 * 0.5, self.y +
                6, 320 * 0.5, self.height
            )
            self.laser_detail = Rect(
                self.x - 320 * 0.5, self.y +
                6 + 8, 320 * 0.5, 48
            )

    def __update_attack_logic(self, delta_time, scene_data):
        if (not self.attacking):
            return

        extend = 48
        if (self.attack_stage == 0):
            if (
                (self.wall == Direction.LEFT and self.x + self.width > extend) or
                (self.wall == Direction.RIGHT and self.x < 320 - extend)
            ):
                self.acceleration.x = 0
                self.velocity.x = 0
                self.attack_stage += 1

        elif (self.attack_stage == 1):
            self.timer_seek.update(delta_time)

            if (not self.timer_seek.done):
                padding = 10
                if (
                    self.y < scene_data.actor.y + scene_data.actor.height - padding and
                    self.y + self.height > scene_data.actor.y + padding
                ):
                    self.acceleration.y = 0
                    self.velocity.y *= 0.25
                    self.attack_stage += 1
                    self.timer_seek.reset()

                    self.__update_laser()

                else:
                    self.acceleration.y = (scene_data.actor.y - self.y) * 0.6
            else:
                self.acceleration.y = 0
                self.velocity.y *= 0.1
                self.attack_stage += 1
                self.timer_seek.reset()

        elif (self.attack_stage == 2):
            self.timer_charge.start()
            self.timer_charge.update(delta_time)
            if (self.timer_charge.done):
                self.timer_charge.reset()

                direction = -1 if self.wall == Direction.LEFT else 1
                self.acceleration.x = direction * 30
                self.velocity.y *= 0.5
                self.attack_stage += 1
                self.__update_laser()

        elif (self.attack_stage == 3):
            self.__update_laser()

            self.timer_laser.start()

            self.timer_laser.update(delta_time)
            if (self.timer_laser.done):
                direction = -1 if self.wall == Direction.LEFT else 1
                self.acceleration.x = direction * 100

                self.timer_laser.reset()
                self.attack_stage += 1

        elif (self.attack_stage == 4):
            if (
                (self.wall == Direction.LEFT and self.x + self.width < -64) or
                (self.wall == Direction.RIGHT and self.x > 320 + 64)
            ):
                self.acceleration = Vector2(0, 0)
                self.velocity = Vector2(0, 0)

                self.attacking = False

    def update(self, delta_time, scene_data):
        self.__update_attack_logic(delta_time, scene_data)
        super(OctoBlaster, self).update(delta_time, scene_data)

    def draw(self, surface):
        if (globals.debugging):
            draw_rectangle(
                surface,
                self.bounds,
                CameraType.STATIC,
                self.color
            )
        else:
            self.sprite.draw(surface, CameraType.STATIC)

            if (self.attack_stage == 3):
                draw_rectangle(
                    surface,
                    self.laser,
                    CameraType.STATIC,
                    Color.SKY_BLUE
                )
                draw_rectangle(
                    surface,
                    self.laser_detail,
                    CameraType.STATIC,
                    Color.WHITE
                )


class Octopus(Boss):
    def __init__(self):
        super(Octopus, self).__init__(96, 64, 128, 48)
        self.sprite_left = Sprite(0, 0, SpriteType.OCTOPUS)
        self.sprite_right = Sprite(160, 0, SpriteType.OCTOPUS)
        self.sprite_right.flip_horizontally(True)

        self.left_arm = OctoArm(self, False)
        self.right_arm = OctoArm(self, True)
        self.blaster = OctoBlaster(self)

        self.stage = 0
        self.attacking = False
        self.attack_started = False
        self.attack_type = 0
        self.timer_attack = Timer(1750)

        self.query_result = None
        self.area = Rect(
            self.x - 8,
            self.y - 8,
            self.width + 8 * 2,
            self.height + 8 * 2
        )

    def reset(self):
        self.left_arm = OctoArm(self, False)
        self.right_arm = OctoArm(self, True)
        self.blaster = OctoBlaster(self)

        self.stage = 0
        self.attacking = False
        self.attack_started = False
        self.attack_type = 0
        self.timer_attack = Timer(1750)

        super(Octopus, self).reset()

    def __update_timer(self, delta_time):
        if (self.attacking):
            return

        self.timer_attack.start()
        self.timer_attack.update(delta_time)
        if (self.timer_attack.done):
            self.attacking = True
            self.timer_attack.reset()

    def __strategize(self, scene_data):
        if (not self.attacking or self.attack_started):
            return

        if (self.stage == 0):
            if (randint(0, 9) < 4):
                self.left_arm.attack()
                self.right_arm.attack()
            else:
                if (
                    scene_data.actor.x + scene_data.actor.width /
                        2 < scene_data.scene_bounds.width * 0.5
                ):
                    self.left_arm.attack()
                else:
                    self.right_arm.attack()
        else:
            if (
                scene_data.actor.x + scene_data.actor.width / 2 < scene_data.scene_bounds.width * 0.33 or
                scene_data.actor.x + scene_data.actor.width /
                    2 > scene_data.scene_bounds.width * 0.66
            ):
                if (randint(0, 9) < 6):
                    self.left_arm.attack()
                    self.right_arm.attack()
                else:
                    if (
                        scene_data.actor.x + scene_data.actor.width /
                            2 < scene_data.scene_bounds.width * 0.5
                    ):
                        self.left_arm.attack()
                    else:
                        self.right_arm.attack()

                self.attack_type = 0
            else:
                if (randint(0, 9) < 2):
                    self.left_arm.attack()
                    self.right_arm.attack()
                    self.attack_type = 0
                else:
                    self.blaster.attack()
                    self.attack_type = 1

        self.attack_started = True

    def __await_attack_result(self):
        if (not self.attack_started):
            return

        if (self.attack_type == 0):
            if (not self.left_arm.attacking and not self.right_arm.attacking):
                self.attack_started = False
                self.attacking = False

        elif (self.attack_type == 1):
            if (not self.blaster.attacking):
                self.attack_started = False
                self.attacking = False

    def __update_stage(self):
        if (self.health < self.total_health * 0.5):
            self.stage = 1
            self.timer_attack.length = 800
        else:
            self.stage = 0

    def __collision(self, scene_data):

        self.query_result = scene_data.kinetic_quad_tree.query(self.area)

        for e in self.query_result:
            if e is self:
                continue

            if isinstance(e, Bullet):
                if (self.bounds.colliderect(e.bounds)):
                    self.hit(e.damage)
                    e.remove = True

    def update(self, delta_time, scene_data):
        if (scene_data.actor == None):
            return

        self.__update_stage()

        self.__update_timer(delta_time)
        self.__strategize(scene_data)
        self.__await_attack_result()

        self.__collision(scene_data)

        self.left_arm.update(delta_time, scene_data)
        self.right_arm.update(delta_time, scene_data)
        self.blaster.update(delta_time, scene_data)

    def draw(self, surface):
        # Draw Body
        self.sprite_left.draw(surface, CameraType.STATIC)
        self.sprite_right.draw(surface, CameraType.STATIC)
        # Draw Arms
        self.left_arm.draw(surface)
        self.right_arm.draw(surface)

        self.blaster.draw(surface)

        if (globals.debugging):
            draw_rectangle(
                surface,
                self.bounds,
                CameraType.STATIC,
                Color.BLUE
            )

        super(Octopus, self).draw(surface)


class GolemPalm(Kinetic):
    def __init__(self, boss, facing_left):
        super(GolemPalm, self).__init__(320, 240 - 32 - 103 / 2, 48, 48, 0)
        self.color = Color.OCEAN_BLUE
        self.sprite = Sprite(0, 64, SpriteType.GOLEM_PALM)
        self.velocity = Vector2(-100, 0)
        self.facing_left = facing_left
        if (not facing_left):
            self.velocity.x = abs(self.velocity.x)
            self.set_location(-71, 240 - 32 - 103 / 2)
            self.sprite.flip_horizontally(True)

        # Kinetic needs this
        self.query_result = None
        self.area = Rect(
            self.x - 8,
            self.y - 8,
            self.width + 8 * 2,
            self.height + 8 * 2
        )

        self.boss = boss

    def set_location(self, x, y):
        super(GolemPalm, self).set_location(x, y)
        self.sprite.set_location(self.x - 16, self.y)

    def __rectanlge_collision_logic(self, entity):
        pass

    def _collision(self, scene_data):
        self._update_collision_rectangles()

        if (globals.debugging):
            for e in scene_data.entities:
                e.set_color(Color.WHITE)

        self.area = Rect(
            self.x - 16,
            self.y - 16,
            self.width + 16 * 2,
            self.height + 16 * 2
        )

        # Check collision against Kinetic stuff (ugly I know)
        self.query_result = scene_data.kinetic_quad_tree.query(self.area)

        for e in self.query_result:
            if e is self:
                continue

            if isinstance(e, Bullet):
                if (self.bounds.colliderect(e.bounds)):
                    self.boss.hit(e.damage)
                    e.remove = True

            if isinstance(e, Player):
                if (self.bounds.colliderect(e.bounds)):
                    e.take_damage()

    def update(self, delta_time, scene_data):
        if (self.facing_left):
            if (self.x + self.width < 0):
                self.remove = True
        else:
            if (self.x > 320):
                self.remove = True

        super(GolemPalm, self).update(delta_time, scene_data)

    def draw(self, surface):
        if (globals.debugging):
            draw_rectangle(
                surface,
                self.bounds,
                CameraType.STATIC,
                self.color
            )
        else:
            self.sprite.draw(surface, CameraType.STATIC)


class GolemHand(Kinetic):
    def __init__(self, boss, attack_time, facing_left):
        super(GolemHand, self).__init__(320, 0, 69, 59, 0)
        self.sprite = Sprite(0, 64, SpriteType.GOLEM_FIST)
        if (not facing_left):
            self.set_location(-69, 0)
            self.sprite.flip_horizontally(True)
        self.init_y = 0

        self.attack_finished = False
        self.resting = False
        self.rising = False

        self.seek_speed = 50
        self.seek_ofs = 0
        self.seek_accel = 50  # lower = faster
        self.attack_accel = 500
        self.attack_speed = 300
        self.rising_speed = -30
        self.attack_timer = Timer(attack_time, True)
        self.charge_timer = Timer(500, False)
        self.rest_timer = Timer(2500, False)

        self.boss = boss
        self.color = Color.TEAL

        self.velocity = Vector2(0, 0)
        self.acceleration = Vector2(0, 0)

        # Kinetic needs this
        self.query_result = None
        self.area = Rect(
            self.x - 8,
            self.y - 8,
            self.width + 8 * 2,
            self.height + 8 * 2
        )

    def set_location(self, x, y):
        super(GolemHand, self).set_location(x, y)
        self.sprite.set_location(self.x, self.y)

    def attack(self):
        self.velocity.x = 0
        if (self.charge_timer.done):
            self.velocity.y = self.attack_speed
            self.acceleration.y = self.attack_accel
            if (self.attack_finished):
                
                self.attack_finished = False
                self.acceleration.y = 0
                self.resting = True
                self.rest_timer.reset()
                self.rest_timer.start()
                self.charge_timer.reset()

    def seek(self, delta_time, scene_data):
        centerPlayer = scene_data.actor.x + scene_data.actor.width / 2 + self.seek_ofs
        centerHand = self.x + self.width / 2
        distance = centerPlayer - centerHand
        new_vel = distance * distance / self.seek_accel
        if (distance < 0):
            self.velocity = Vector2(-new_vel, 0)
        elif (centerPlayer - centerHand > 0):
            self.velocity = Vector2(new_vel, 0)

        if (abs(self.velocity.x) > self.seek_speed):
            self.velocity.x = self.seek_speed if self.velocity.x > 0 else -self.seek_speed

    def __rectanlge_collision_logic(self, entity):
        if self.collision_rectangles[1].colliderect(entity.bounds) and self.velocity.y > 0:
            self.set_location(self.x, entity.bounds.top - self.bounds.height)
            if (not self.attack_finished):
                play_sound("smash.wav", 0.3)
            self.attack_finished = True
            

    def _collision(self, scene_data):
        self._update_collision_rectangles()

        if (globals.debugging):
            for e in scene_data.entities:
                e.set_color(Color.WHITE)

        self.area = Rect(
            self.x - 16,
            self.y - 16,
            self.width + 16 * 2,
            self.height + 16 * 2
        )

        self.query_result = scene_data.entity_quad_tree.query(self.area)

        for e in self.query_result:
            if e is self:
                continue

            if isinstance(e, Block):
                self.__rectanlge_collision_logic(e)

            if (globals.debugging):
                e.set_color(Color.RED)

        # Check collision against Kinetic stuff (ugly I know)
        self.query_result = scene_data.kinetic_quad_tree.query(self.area)

        for e in self.query_result:
            if e is self:
                continue

            if isinstance(e, Bullet):
                if (self.bounds.colliderect(e.bounds)):
                    self.boss.hit(e.damage)
                    e.remove = True

            if isinstance(e, Player):
                if (self.bounds.colliderect(e.bounds) and not self.attack_finished):
                    e.take_damage()

    def update(self, delta_time, scene_data):
        self.attack_timer.update(delta_time)
        self.rest_timer.update(delta_time)
        self.charge_timer.update(delta_time)

        if (scene_data.actor == None):
            return

        if (not self.attack_timer.done):
            self.seek(delta_time, scene_data)
        elif (self.resting):
            if (self.rest_timer.done):
                self.resting = False
                self.rising = True
        elif (self.rising):
            self.velocity.y = self.rising_speed
            if (self.y <= 0):
                self.velocity.y = 0
                self.rising = False
                self.attack_timer.reset()
                self.attack_timer.start()
        else:
            if (self.y + self.height >= scene_data.scene_bounds.height - 32):
                self.attack_finished = True
            if (not self.charge_timer.started):
                self.charge_timer.start()
            self.attack()

        super(GolemHand, self).update(delta_time, scene_data)

    def draw(self, surface):
        if (globals.debugging):
            draw_rectangle(
                surface,
                self.bounds,
                CameraType.DYNAMIC,
                self.color
            )
        else:
            self.sprite.draw(surface, CameraType.STATIC)


class Golem(Boss):
    def __init__(self):
        super(Golem, self).__init__(112, 32, 96, 16)
        self.sprite_body_left = Sprite(80, 0, SpriteType.GOLEM_BODY)
        self.sprite_body_right = Sprite(80 + 5 * 16, 0, SpriteType.GOLEM_BODY)
        self.sprite_body_right.flip_horizontally(True)

        self.right_hand = GolemHand(self, 2500, False)
        self.left_hand = GolemHand(self, 4500, True)
        self.palms = []
        self.palm_timer = Timer(10000, False)
        self.next_checkpoint = self.total_health * 0.75

        self.query_result = None
        self.area = Rect(
            self.x - 8,
            self.y - 8,
            self.width + 8 * 2,
            self.height + 8 * 2
        )

    def reset(self):
        self.right_hand = GolemHand(self, 2500, False)
        self.left_hand = GolemHand(self, 4500, True)
        self.palms = []

        self.palm_timer = Timer(10000, False)
        self.next_checkpoint = self.total_health * 0.75

        super(Golem, self).reset()

    def __change_stage(self, scene_data):
        if (self.health < self.total_health * 0.25):
            # final stage: faster smashes, even more palms
            self.palm_timer.length = 5500
            self.right_hand.attack_timer.length = 2000
            self.left_hand.attack_timer.length = 3500
            self.right_hand.rising_speed *= 2
            self.left_hand.rising_speed *= 2
            self.next_checkpoint = -1
        elif (self.health < self.total_health * 0.5):
            # stage 2: more palms
            self.palm_timer.length = 7000
            self.next_checkpoint = self.total_health * 0.25
        elif (self.health < self.total_health * 0.75):
            # stage 1: enable palms
            if (scene_data.actor.x + scene_data.actor.width * 0.5 > scene_data.scene_bounds.width * 0.5):
                self.palms.append(GolemPalm(self, False))
            else:
                self.palms.append(GolemPalm(self, True))
            self.palm_timer.reset()
            self.palm_timer.start()
            self.next_checkpoint = self.total_health * 0.5

    def __update_stage_change(self, scene_data):
        if self.health < self.next_checkpoint:
            self.__change_stage(scene_data)

    def __collision(self, scene_data):
        self.query_result = scene_data.kinetic_quad_tree.query(self.area)

        for e in self.query_result:
            if e is self:
                continue

            if isinstance(e, Bullet):
                if (self.bounds.colliderect(e.bounds)):
                    self.hit(e.damage * 0.6)
                    e.remove = True

    def update(self, delta_time, scene_data):
        if (scene_data.actor == None):
            return

        self.__collision(scene_data)
        self.__update_stage_change(scene_data)
        self.palm_timer.update(delta_time)
        if (self.palm_timer.done):
            if (scene_data.actor.x + scene_data.actor.width * 0.5 > scene_data.scene_bounds.width / 2):
                self.palms.append(GolemPalm(self, False))
            else:
                self.palms.append(GolemPalm(self, True))
            self.palm_timer.reset()
            self.palm_timer.start()

        if (not self.right_hand.attack_timer.done and not self.left_hand.attack_timer.done):
            # both in air
            self.right_hand.seek_ofs = -64
            self.left_hand.seek_ofs = 64
        else:
            self.right_hand.seek_ofs = 0
            self.left_hand.seek_ofs = 0

        self.right_hand.update(delta_time, scene_data)

        self.left_hand.update(delta_time, scene_data)
        for p in self.palms:
            p.update(delta_time, scene_data)

    def draw(self, surface):
        self.sprite_body_left.draw(surface, CameraType.STATIC)
        self.sprite_body_right.draw(surface, CameraType.STATIC)

        self.right_hand.draw(surface)
        self.left_hand.draw(surface)
        for p in self.palms:
            p.draw(surface)

        super(Golem, self).draw(surface)
