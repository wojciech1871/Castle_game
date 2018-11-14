import pygame
from pygame.locals import *
import os
from GameModel import *

if not pygame.font:
    print("Warning, fonts disabled")
if not pygame.mixer:
    print("Warning, sound disabled")


class FunContainer:
    main_dir = os.path.split(os.path.abspath(__file__))[0]
    data_dir = os.path.join(main_dir, "resources")

    def __init__(self):
        pass

    @classmethod
    def load_image(cls, name, colorkey=None):
        fullname = os.path.join(cls.data_dir, name)
        try:
            image = pygame.image.load(fullname)
        except pygame.error:
            print("Cannot load image {}".format(name))
            raise SystemExit
        image = image.convert()
        if colorkey is not None:
            if colorkey is -1:
                colorkey = image.get_at((0, 0))
            image.set_colorkey(colorkey, RLEACCEL)
        return image

    @classmethod
    def load_sound(cls, name):
        class NoneSound:
            def play(self): pass

        if not pygame.mixer:
            return NoneSound()
        fullname = os.path.join(cls.data_dir, name)
        try:
            sound = pygame.mixer.Sound(fullname)
        except pygame.error:
            print("Cannot load sound: {}".format(name))
            raise SystemExit
        return sound

    @classmethod
    def center_blit(cls, destination: pygame.Surface, image: pygame.Surface, area: pygame.Rect):
        imageRect = image.get_rect()
        imageRect.center = area.center
        destination.blit(image, imageRect)


class Ball(pygame.sprite.Sprite):
    resolution = (35, 35)
    color = None

    def __init__(self):
        super().__init__()
        self.image = None
        self.imageBase = None
        self.imageOnFocus = None
        self.rect = None
        self.rectBase = None
        self.rectOnFocus = None
        self.boardPos = None

    def on_init(self):
        self.imageOnFocus = pygame.transform.scale(self.image, (self.resolution[0] + 5, self.resolution[1] + 5))
        self.imageBase = pygame.transform.scale(self.image, (self.resolution[0], self.resolution[1]))
        self.image = self.imageBase
        self.rectOnFocus = self.imageOnFocus.get_rect()
        self.rectBase = self.imageBase.get_rect()
        self.rect = self.rectBase

    def set_position(self, rect: Rect, position):
        self.rect.center = rect.center
        self.boardPos = position

    def clicked(self):
        self.image = self.imageOnFocus
        center = self.rect.center
        self.rect = self.rectOnFocus
        self.rect.center = center

    def unclicked(self):
        self.image = self.imageBase
        center = self.rect.center
        self.rect = self.rectBase
        self.rect.center = center

    def update(self):
        pass


class WhiteBall(Ball):
    color = GameColor.WHITE

    def __init__(self):
        super().__init__()
        self.image = FunContainer.load_image("white-ball.jpg", -1)
        self.on_init()


class BlackBall(Ball):
    color = GameColor.BLACK

    def __init__(self):
        super().__init__()
        self.image = FunContainer.load_image("black-ball.jpg", -1)
        self.on_init()


class BallsContainer(pygame.sprite.RenderPlain):
    def __init__(self):
        super().__init__()
    
    def clicked_sprite(self, position):
        for sprite in self.sprites():
            if sprite.rect.collidepoint(position):
                return sprite
        return None


class Fire(pygame.sprite.Sprite):
    resolution = (50, 50)

    def __init__(self):
        super().__init__()
        self.image = FunContainer.load_image("fire.jpg", -1)
        self.image = pygame.transform.scale(self.image, self.resolution)
        self.rect = self.image.get_rect()

    def set_rect(self, rect):
        self.rect.center = rect.center


class Gauntlet(pygame.sprite.Sprite):
    resolution = (60, 60)

    def __init__(self):
        super().__init__()
        self.image = FunContainer.load_image("gauntlet2.jpg", -1)
        self.clickedImage = pygame.transform.scale(self.image, (self.resolution[0]-8, self.resolution[1]-8))
        self.normalImage = pygame.transform.scale(self.image, self.resolution)
        self.image = self.normalImage
        self.rect = self.image.get_rect()
        pygame.mouse.set_visible(False)

    def update(self):
        self.rect.midtop = pygame.mouse.get_pos()

    def clicked(self):
        self.image = self.clickedImage

    def unclicked(self):
        self.image = self.normalImage


class Player:
    def __init__(self):
        self.color = None
        self.balls = None


class GameView(FunContainer):
    windowWidth = 800
    windowHeight = 800
    marginWidth = 10
    marginHeight = 10

    numOfCells = GameModel.numOfCells

    cellWidth = np.floor_divide(windowWidth-2*marginWidth, numOfCells)
    marginWidth += np.floor_divide(np.remainder(windowWidth-2*marginWidth, numOfCells), 2)
    cellHeight = np.floor_divide(windowHeight-2*marginHeight, numOfCells)
    marginHeight += np.floor_divide(np.remainder(windowHeight-2*marginHeight, numOfCells), 2)
    linesColor = Color(25, 25, 110)
    windowName = "Castle game"

    def __init__(self):
        super().__init__()
        pygame.init()
        self.gameModel = GameModel()
        self.board = self.board_init()
        self.screen = pygame.display.set_mode((self.windowWidth, self.windowHeight))
        pygame.display.set_caption(self.windowName)
        self.background = FunContainer.load_image("background.jpg")
        self.background = pygame.transform.scale(self.background, (self.windowWidth, self.windowHeight))
        self.draw_lines()
        self.draw_thrones()

        self.draw_walls()
        self.screen.blit(self.background, (0, 0))

        self.clock = pygame.time.Clock()

        self.fire = Fire()
        self.gauntlet = Gauntlet()

        self.blackBalls = BallsContainer()
        self.whiteBalls = BallsContainer()
        self.balls_init()

        self.blackBalls.draw(self.screen)
        self.whiteBalls.draw(self.screen)

        self.playerMoving = GameColor.WHITE
        self.ballsMoving = self.whiteBalls
        pygame.display.update()

    def board_init(self):
        board = np.array([[Rect([0]*4)]*self.numOfCells]*self.numOfCells)
        for i in range(self.numOfCells):
            for j in range(self.numOfCells):
                board[j][i] = Rect(i*self.cellWidth+self.marginWidth, j*self.cellHeight+self.marginHeight, self.cellWidth-1, self.cellHeight-1)
        return board

    def cartesian2board(self, pos):
        x = np.floor_divide(pos[1] - self.marginWidth, self.cellWidth)
        if x >= self.numOfCells:
            x = self.numOfCells - 1
        elif x <= 0:
            x = 0
        y = np.floor_divide(pos[0] - self.marginHeight, self.cellHeight)
        if y >= self.numOfCells:
            y = self.numOfCells - 1
        elif y <= 0:
            y = 0
        return x, y

    def draw_lines(self):
        for i in range(self.numOfCells):
            start = Rect(self.board[i][0]).center
            stop = Rect(self.board[i][self.numOfCells-1]).center
            pygame.draw.line(self.background, self.linesColor, start, stop, 1)
        for j in range(self.numOfCells):
            start = Rect(self.board[0][j]).center
            stop = Rect(self.board[self.numOfCells-1][j]).center
            pygame.draw.line(self.background, self.linesColor, start, stop, 1)

    def draw_thrones(self):
        resolution = (60, 60)
        blueThrone = self.load_image("blue-throne.jpg", -1)
        redThrone = self.load_image("red-throne.jpg", -1)
        blueThrone = pygame.transform.scale(blueThrone, resolution)
        redThrone = pygame.transform.scale(redThrone, resolution)
        self.center_blit(self.background, blueThrone, Rect(self.board[self.gameModel.blackThronePos]))
        self.center_blit(self.background, redThrone, Rect(self.board[self.gameModel.whiteThronePos]))


    def draw_walls(self):
        resolution = (42, 42)
        wallImage = self.load_image("wall.jpg")
        wallImage = pygame.transform.scale(wallImage, resolution)
        for i in range(self.numOfCells):
            for j in range(self.numOfCells):
                if self.gameModel.wallsMap[i][j]:
                    self.center_blit(self.background, wallImage, Rect(self.board[(i, j)]))

    def balls_init(self):
        for i in range(self.numOfCells):
            for j in range(self.numOfCells):
                if self.gameModel.ballsMap[(i, j)]:
                    if self.gameModel.ballsMap[(i, j)] == GameColor.WHITE:
                        ball = WhiteBall()
                        self.place_ball(ball, (i, j))
                        self.whiteBalls.add(ball)
                    else:
                        ball = BlackBall()
                        self.place_ball(ball, (i, j))
                        self.blackBalls.add(ball)

    def change_player(self):
        if self.gameModel.activeColor == GameColor.WHITE:
            self.gameModel.activeColor = GameColor.BLACK
            self.ballsMoving = self.blackBalls
        else:
            self.gameModel.activeColor = GameColor.WHITE
            self.ballsMoving = self.whiteBalls
    
    def place_ball(self, ball: Ball, boardPos: tuple):
        self.gameModel.ballsMap[boardPos] = ball.color
        ball.set_position(Rect(self.board[boardPos]), boardPos)


    def beat(self, boardPos: tuple, ballColor: GameColor):
        ballsContainer = None
        if ballColor == GameColor.WHITE:
            ballsContainer = self.whiteBalls
        else:
            ballsContainer = self.blackBalls
        rect = Rect(self.board[boardPos])
        sprite = ballsContainer.clicked_sprite(rect.center)
        sprite.kill()
        self.fire.set_rect(rect)
        self.center_blit(self.screen, self.fire.image, self.fire.rect)
        pygame.display.update()
        pygame.time.delay(500)
        self.screen.blit(self.background, self.fire.rect, self.fire.rect)

    def move_ball(self, ball: Ball, endPos: tuple) -> bool:
        startPos = ball.boardPos
        if not self.gameModel.valid_move(ball.color, startPos, endPos):
            return False
        else:
            if self.gameModel.ballsMap[endPos]:
                self.beat(endPos, GameColor.second_color(ball.color))
            self.gameModel.ballsMap[startPos] = None
            self.place_ball(ball, endPos)
            return True

    def view_update(self):
        self.screen.blit(self.background, self.gauntlet.rect, self.gauntlet.rect)

        self.blackBalls.update()
        self.blackBalls.clear(self.screen, self.background)
        self.blackBalls.draw(self.screen)

        self.whiteBalls.update()
        self.whiteBalls.clear(self.screen, self.background)
        self.whiteBalls.draw(self.screen)

        self.gauntlet.update()
        self.screen.blit(self.gauntlet.image, self.gauntlet.rect)

        pygame.display.update()
