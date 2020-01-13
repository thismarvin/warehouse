import os
import pygame
from enum import IntEnum
from pygine.base import PygineObject
from pygine.draw import draw_image
from pygine import globals
from pygine.sounds import load_sound_paths
from pygine.utilities import Timer


SPRITE_SHEET = None
TEXT_SHEET = None

BOSS_BACKGROUNDS = []
BOSS_SPRITES = []

BACKGROUNDS = []

def load_content():
    global SPRITE_SHEET
    global TEXT_SHEET

    path = os.path.dirname(os.path.abspath(__file__))

    SPRITE_SHEET = pygame.image.load(
        path + "/assets/sprites/sprites.png"
    )
    TEXT_SHEET = pygame.image.load(
        path + "/assets/sprites/font.png"
    )
    __load_layers()

    load_sound_paths()


def __load_layers():
    # Load Extra backgrounds
    path = os.path.dirname(os.path.abspath(__file__)) + \
        "/assets/sprites/bosses/"

    BOSS_BACKGROUNDS.append(pygame.image.load(
        path + "boss_0_background.png").convert())
    BOSS_BACKGROUNDS.append(pygame.image.load(
        path + "boss_1_background.png").convert())
    BOSS_BACKGROUNDS.append(pygame.image.load(
        path + "boss_2_background.png").convert())

    BOSS_SPRITES.append(pygame.image.load(
        path + "boss_0_sprites.png").convert_alpha())
    BOSS_SPRITES.append(pygame.image.load(
        path + "boss_1_sprites.png").convert_alpha())
    BOSS_SPRITES.append(pygame.image.load(
        path + "boss_2_sprites.png").convert_alpha())

    path = os.path.dirname(os.path.abspath(__file__)) + \
        "/assets/sprites/"
    BACKGROUNDS.append(pygame.image.load(
        path + "title.png").convert()
    )
    BACKGROUNDS.append(pygame.image.load(
        path + "select.png").convert()
    )
    BACKGROUNDS.append(pygame.image.load(
        path + "lore.png").convert()
    )



class SpriteType(IntEnum):
    NONE = 0
    TEXT = 1
    TITLE = 2
    SELECT = 3
    PLAYERA = 4
    PLAYERB = 5

    BACKGROUND_0 = 6
    BACKGROUND_1 = 7
    BACKGROUND_2 = 8

    OCTOPUS = 9

    GOLEM_FIST = 10
    GOLEM_PALM = 11
    GOLEM_BODY = 12
    GOLEM_CORE = 13

    GUN_0_H = 24
    GUN_0_V = 25
    GUN_1_H = 30
    GUN_1_V = 31
    BULLET = 26

    OCTOPUS_ARM = 27
    OCTOPUS_GUN = 28    

    LORE = 69


class Sprite(PygineObject):
    def __init__(self, x, y, sprite_type=SpriteType.NONE):
        super(Sprite, self).__init__(x, y, 0, 0)

        self.sprite_sheet = SPRITE_SHEET
        self.set_sprite(sprite_type)

    def set_sprite(self, sprite_type):
        self.type = sprite_type
        self.__load_sprite()

    def set_frame(self, frame, columns):
        self.__sprite_x = self.__original_sprite_x + frame % columns * self.width
        self.__sprite_y = self.__original_sprite_y + \
            int(frame / columns) * self.height
        self.__apply_changes_to_sprite()

    def increment_sprite_x(self, increment):
        self.__sprite_x += increment
        self.__apply_changes_to_sprite()

    def increment_sprite_y(self, increment):
        self.__sprite_y += increment
        self.__apply_changes_to_sprite()

    def flip_horizontally(self, flip):
        if flip:
            self.image = pygame.transform.flip(
                self.image, True, False).convert_alpha()
        else:
            self.image = pygame.transform.flip(
                self.image, False, False).convert_alpha()

    def flip_vertically(self, flip):
        if flip:
            self.image = pygame.transform.flip(
                self.image, False, True).convert_alpha()
        else:
            self.image = pygame.transform.flip(
                self.image, False, False).convert_alpha()

    def __sprite_setup(self, sprite_x=0, sprite_y=0, width=0, height=0):
        self.__original_sprite_x = sprite_x
        self.__original_sprite_y = sprite_y
        self.__sprite_x = sprite_x
        self.__sprite_y = sprite_y
        self.set_width(width)
        self.set_height(height)

    def __load_sprite(self):
        if self.type == SpriteType.NONE:
            self.__sprite_setup(0, 0, 16, 16)

        elif (self.type == SpriteType.TEXT):
            self.__sprite_setup(0, 0, 8, 8)
            self.sprite_sheet = TEXT_SHEET

        elif (self.type == SpriteType.TITLE):
            self.__sprite_setup(0, 0, 320, 240)
            self.sprite_sheet = BACKGROUNDS[0]
        elif (self.type == SpriteType.SELECT):
            self.__sprite_setup(0, 0, 320, 240)
            self.sprite_sheet = BACKGROUNDS[1]

        elif (self.type == SpriteType.LORE):
            self.__sprite_setup(0, 0, 320, 240)
            self.sprite_sheet = BACKGROUNDS[2]

        elif (self.type == SpriteType.PLAYERA):
            self.__sprite_setup(0, 32, 32, 48)
        elif (self.type == SpriteType.PLAYERB):
            self.__sprite_setup(32, 32, 32, 48)

        elif (self.type == SpriteType.BACKGROUND_0):
            self.__sprite_setup(0, 0, 320, 240)
            self.sprite_sheet = BOSS_BACKGROUNDS[0]
        elif (self.type == SpriteType.BACKGROUND_1):
            self.__sprite_setup(0, 0, 320, 240)
            self.sprite_sheet = BOSS_BACKGROUNDS[1]
        elif (self.type == SpriteType.BACKGROUND_2):
            self.__sprite_setup(0, 0, 320, 240)
            self.sprite_sheet = BOSS_BACKGROUNDS[2]

        elif (self.type == SpriteType.OCTOPUS):
            self.__sprite_setup(0, 0, 160, 192)
            self.sprite_sheet = BOSS_SPRITES[0]

        elif (self.type == SpriteType.OCTOPUS_ARM):
            self.__sprite_setup(0, 192, 144, 64)
            self.sprite_sheet = BOSS_SPRITES[0]
        elif (self.type == SpriteType.OCTOPUS_GUN):
            self.__sprite_setup(160, 176, 96, 80)
            self.sprite_sheet = BOSS_SPRITES[0]

        elif (self.type == SpriteType.GOLEM_FIST):
            self.__sprite_setup(80, 0, 80, 64)
            self.sprite_sheet = BOSS_SPRITES[1]
        elif (self.type == SpriteType.GOLEM_PALM):
            self.__sprite_setup(80, 64, 80, 112)
            self.sprite_sheet = BOSS_SPRITES[1]
        elif (self.type == SpriteType.GOLEM_BODY):
            self.__sprite_setup(0, 0, 80, 192)
            self.sprite_sheet = BOSS_SPRITES[1]
        elif (self.type == SpriteType.GOLEM_CORE):
            self.__sprite_setup(0, 0, 16, 16)
            self.sprite_sheet = BOSS_SPRITES[1]

        elif (self.type == SpriteType.GUN_0_H):
            self.__sprite_setup(64, 32, 26, 19)
        elif (self.type == SpriteType.GUN_0_V):
            self.__sprite_setup(64, 52, 19, 26)

        elif (self.type == SpriteType.GUN_1_H):
            self.__sprite_setup(128, 32, 26, 19)
        elif (self.type == SpriteType.GUN_1_V):
            self.__sprite_setup(128, 52, 19, 26)

        elif (self.type == SpriteType.BULLET):
            self.__sprite_setup(96, 32, 16, 16)

        self.__apply_changes_to_sprite()

    def __apply_changes_to_sprite(self):
        self.image = pygame.Surface(
            (self.width, self.height), pygame.SRCALPHA).convert_alpha()

        self.image.blit(self.sprite_sheet, (0, 0),
                        (self.__sprite_x, self.__sprite_y, self.width, self.height))

    def draw(self, surface, camera_type):
        draw_image(surface, self.image, self.bounds, camera_type)


class Animation:
    def __init__(self, total_frames, columns, frame_duration):
        self.total_frames = total_frames
        self.columns = columns
        self.__frame_duration = frame_duration
        self.current_frame = 0
        self.__timer = Timer(self.__frame_duration)
        self.__timer.start()

    def update(self, delta_time):
        self.__timer.update(delta_time)
        if self.__timer.done:
            self.current_frame = self.current_frame + \
                1 if self.current_frame + 1 < self.total_frames else 0
            self.__timer.reset()
            self.__timer.start()


class Text(PygineObject):
    def __init__(self, x, y, value):
        super(Text, self).__init__(x, y, 8, 8)

        self.value = value
        self.set_value(self.value)

    def set_value(self, value):
        self.value = value

        self.sprites = []
        for i in range(len(self.value)):
            self.sprites.append(
                Sprite(self.x + i * self.width, self.y, SpriteType.TEXT))

        for i in range(len(self.value)):
            self.sprites[i].set_frame(ord(list(self.value)[i]), 16)

        self.sprites.sort(key=lambda e: -e.x)

    def draw(self, surface, camera_type):
        for s in self.sprites:
            s.draw(surface, camera_type)
