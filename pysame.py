#!/usr/bin/env python
import sys
import os.path
import pygame
import random


##  Resource
##
class Resource(object):

    def __init__(self, path):
        self.path = path
        self._font = {}
        self._image = {}
        self._sound = {}
        return
        
    def get_font(self, name, size):
        k = (name, size)
        if k in self._font:
            font = self._font[k]
        else:
            path = os.path.join(self.path, name)
            font = pygame.font.Font(path, size)
            self._font[k] = font
        return font

    def get_image(self, name):
        if name in self._image:
            image = self._image[name]
        else:
            path = os.path.join(self.path, name)
            image = pygame.image.load(path)
            self._image[name] = image.convert()
        return image

    def get_sound(self, name):
        if name in self._sound:
            sound = self._sound[name]
        else:
            path = os.path.join(self.path, name)
            sound = pygame.mixer.Sound(path)
            self._sound[name] = sound
        return sound

        
##  Board
##
class Board(object):

    BORDER_COLOR = (0,0,0)
    HIGHLIGHT_COLOR = (255,255,255)
    
    class Group(object):

        def __init__(self, i):
            self.i = i
            self.parent = None
            self.blocks = []
            return

        def __repr__(self):
            return '<%r: %r>' % (self.i, self.blocks)

        def __len__(self):
            return len(self.blocks)

        def __iter__(self):
            return iter(self.blocks)

        def add(self, block):
            self.blocks.append(block)
            return

    def __init__(self, (bwidth, bheight), images, blocksize=32):
        self.bwidth = bwidth
        self.bheight = bheight
        self.images = images
        self.blocksize = blocksize
        return

    def reset(self, ntypes=6, skew=1.5):
        types = range(ntypes)
        random.shuffle(types)
        dist = []
        n = 1.0
        for b in types:
            dist.extend([b]*int(n))
            n *= skew
        self._block = []
        for x in xrange(self.bwidth):
            row = [ random.choice(dist) for y in xrange(self.bheight) ]
            self._block.append(row)
        self._update_groups()
        return

    def get_bwidth(self):
        return len(self._block)

    def get_size(self):
        return (self.get_bwidth()*self.blocksize,
                self.bheight*self.blocksize)

    def get_ngroups(self):
        groups = set()
        for group in self._groups.itervalues():
            if 2 <= len(group):
                groups.add(group)
        return len(groups)

    def get_nblocks(self):
        return sum( len([ 1 for b in row if b is not None])
                    for row in self._block )

    def get_blocks(self, pos):
        blocks = set()
        if pos in self._groups:
            group = self._groups[pos]
            blocks.update(group)
        return blocks
        
    def get_block_rect(self, blocks):
        rect = None
        for (x,y) in blocks:
            r = pygame.Rect(x*self.blocksize,
                            (self.bheight-1-y)*self.blocksize,
                            self.blocksize, self.blocksize)
            if rect is None:
                rect = r
            else:
                rect.union_ip(r)
        return rect
        
    def get_block_pos(self, (x,y)):
        bwidth = self.get_bwidth()
        x = x/self.blocksize
        y = y/self.blocksize
        if x < 0 or bwidth <= x or y < 0 or self.bheight <= y:
            raise ValueError((x,y))
        return (x, y)

    def remove_blocks(self, blocks):
        rows = set()
        for (x,y) in blocks:
            self._block[x][y] = None
            rows.add(x)
        for x in rows:
            row = self._block[x]
            y1 = 0
            while y1 < len(row):
                if row[y1] is not None:
                    y1 += 1
                    continue
                for y0 in xrange(y1+1, len(row)):
                    if row[y0] is not None:
                        row[y1] = row[y0]
                        row[y0] = None
                        break
                else:
                    row[y1] = None
                    y1 += 1
        self._block = [ row for row in self._block if row[0] is not None ]
        self._update_groups()
        return
        
    def render(self, selection):
        surface = pygame.Surface(self.get_size(), pygame.SRCALPHA)
        surface.fill((0,0,0,0))
        self._paint_blocks(surface)
        self._paint_selection(surface, selection)
        return surface

    def _update_groups(self):
        # clustering
        josh = {}
        i = 0
        bwidth = self.get_bwidth()
        for x in xrange(bwidth):
            for y in xrange(self.bheight):
                pos0 = (x,y)
                block0 = self._block[x][y]
                if block0 is None: continue
                if pos0 in josh:
                    group0 = josh[pos0]
                    while group0.parent is not None:
                        group0 = group0.parent
                else:
                    group0 = josh[pos0] = self.Group(i)
                    i += 1
                neighbours = []
                if x+1 < bwidth:
                    neighbours.append( ((x+1,y), self._block[x+1][y]) )
                if y+1 < self.bheight:
                    neighbours.append( ((x,y+1), self._block[x][y+1]) )
                for (pos1,block1) in neighbours:
                    if block1 is None: continue
                    if block1 != block0: continue
                    if pos0 not in josh:
                        assert 0
                    elif pos1 not in josh:
                        josh[pos1] = josh[pos0]
                    else:
                        group1 = josh[pos1]
                        while group1.parent is not None:
                            group1 = group1.parent
                        assert group1 is not None
                        if group1 is not group0:
                            group1.parent = group0
        self._groups = {}
        for (pos,group) in josh.iteritems():
            while group.parent is not None:
                group = group.parent
            group.add(pos)
            self._groups[pos] = group
        return

    def _paint_blocks(self, surface):
        bwidth = self.get_bwidth()
        lines = []
        for x in xrange(bwidth):
            row = self._block[x]
            for y in xrange(len(row)):
                block = row[y]
                if block is None: continue
                rect = self.get_block_rect([(x,y)])
                src = pygame.Rect(block*self.blocksize, 0,
                                  self.blocksize, self.blocksize)
                surface.blit(self.images, rect, src)
                group = self._groups.get((x,y))
                if group is not self._groups.get((x+1,y)):
                    lines.append((rect.topright, rect.bottomright))
                if group is not self._groups.get((x,y+1)):
                    lines.append((rect.topleft, rect.topright))
        for (p1,p2) in lines:
            pygame.draw.line(surface, self.BORDER_COLOR, p1, p2)
        return

    def _paint_selection(self, surface, selection):
        lines = []
        for (x,y) in selection:
            block = self._block[x][y]
            rect = self.get_block_rect([(x,y)])
            src = pygame.Rect(block*self.blocksize, self.blocksize,
                              self.blocksize, self.blocksize)
            surface.blit(self.images, rect, src)
            group = self._groups.get((x,y))
            if group is not self._groups.get((x-1,y)):
                lines.append((rect.topleft, rect.bottomleft))
            if group is not self._groups.get((x+1,y)):
                lines.append((rect.topright, rect.bottomright))
            if group is not self._groups.get((x,y-1)):
                lines.append((rect.bottomleft, rect.bottomright))
            if group is not self._groups.get((x,y+1)):
                lines.append((rect.topleft, rect.topright))
        for (p1,p2) in lines:
            pygame.draw.line(surface, self.HIGHLIGHT_COLOR, p1, p2, 2)
        return


##  PySame
##
class PySame(object):

    class Particle(object):

        def __init__(self, surface, rect, count):
            self.surface = surface
            self.rect = rect
            self.count = count
            return

        def __repr__(self):
            return '<Particle: %r %r>' % (self.surface, self.rect)

        def update(self):
            self.count -= 1
            self.rect.y -= 2
            return
            
    TEXT_COLOR = (255,255,255)
    SHADOW_COLOR = (40,40,40)
    SHADOW_DIST = 2

    def __init__(self, resource, surface,
                 boardsize=(20,15), blocksize=32):
        self.resource = resource
        self.blocksize = blocksize
        self.surface = surface
        self.font = self.resource.get_font('prstartk.ttf', blocksize)
        self.background = self.resource.get_image('background.png')
        self.sound_remove = self.resource.get_sound('remove2.wav')
        self._board = Board(boardsize,
                            self.resource.get_image('blocks.png'),
                            blocksize=self.blocksize)
        return

    def start(self):
        self._ingame = True
        self._board.reset()
        self._score = 0
        self._particles = []
        self._selection = set()
        self._boardcache = None
        return

    def repaint(self):
        self.surface.blit(self.background, (0,0))
        (width,height) = self.surface.get_size()
        if self._boardcache is None:
            self._boardcache = self._board.render(self._selection)
        (w,h) = self._boardcache.get_size()
        self.surface.blit(self._boardcache, ((width-w)/2,height-h))
        for part in self._particles:
            self.surface.blit(part.surface, part.rect)
        text = (u'SCORE:%d' % self._score)
        self._render_text(text, self.TEXT_COLOR, (-1,-1), (-1,-1))
        text = (u'LEFT:%d' % self._board.get_nblocks())
        self._render_text(text, self.TEXT_COLOR, (+1,-1), (+1,-1))
        if not self._ingame:
            self._render_text(u'GAME OVER', self.TEXT_COLOR)
        pygame.display.flip()
        return

    def update(self):
        for part in self._particles:
            part.update()
        self._particles = [ part for part in self._particles
                            if 0 < part.count ]
        self.repaint()
        return

    def key_down(self, key):
        if self._ingame:
            pass
        else:
            self.start()
        return

    def mouse_move(self, p):
        if self._ingame:
            self._update_selection(p)
        return

    def mouse_button(self, p):
        if self._ingame:
            self._remove_selection()
            self._update_selection(p)
        else:
            self.start()
        return

    def _add_particle(self, surface, (x,y)):
        (w,h) = surface.get_size()
        part = self.Particle(surface, pygame.Rect(x-w/2, y-h/2, w, h), 10)
        self._particles.append(part)
        return

    def _render_text(self, text, color, pos=(0,0), align=(0,0)):
        glyph = self.font.render(text, 1, color)
        (width,height) = self.surface.get_size()
        (w,h) = glyph.get_size()
        (px,py) = pos
        (dx,dy) = align
        x = (1+px)*width/2-(1+dx)*w/2
        y = (1+py)*height/2-(1+dy)*h/2
        d = self.SHADOW_DIST
        shadow = self.font.render(text, 1, self.SHADOW_COLOR)
        self.surface.blit(shadow, (x+d,y+d))
        self.surface.blit(glyph, (x,y))
        return

    def _get_board_pos(self):
        (width,height) = self.surface.get_size()
        (w,h) = self._board.get_size()
        x = (width-w)/2
        y = height-h
        return (x,y)

    def _get_block_pos(self, (x,y)):
        (w,h) = self._board.get_size()
        (dx,dy) = self._get_board_pos()
        return self._board.get_block_pos((x-dx,h-(y-dy)))

    def _update_selection(self, pos):
        try:
            p = self._get_block_pos(pos)
        except ValueError:
            return
        blocks = self._board.get_blocks(p)
        if 2 <= len(blocks):
            selection = blocks
        else:
            selection = set()
        if self._selection != selection:
            self._selection = selection
            self._boardcache = None
        return

    def _remove_selection(self):
        n = len(self._selection)
        if not n: return
        self._score += n*n
        self.sound_remove.play()
        rect = self._board.get_block_rect(self._selection)
        surface = self.font.render(str(n), 1, self.TEXT_COLOR)
        (x,y) = rect.center
        (dx,dy) = self._get_board_pos()
        self._add_particle(surface, (x+dx,y+dy))
        self._board.remove_blocks(self._selection)
        if self._board.get_ngroups() == 0:
            self._ingame = False
        self._selection = set()
        self._boardcache = None
        return
        
    def run(self, msec=50):
        loop = True
        pygame.time.set_timer(pygame.USEREVENT, msec)
        while loop:
            ev = pygame.event.wait()
            if ev.type == pygame.QUIT:
                loop = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    loop = False
                else:
                    self.key_down(ev.key)
            elif ev.type == pygame.VIDEOEXPOSE:
                self.repaint()
            elif ev.type == pygame.USEREVENT:
                self.update()
            elif ev.type == pygame.MOUSEMOTION:
                self.mouse_move(ev.pos)
            elif ev.type == pygame.MOUSEBUTTONUP:
                self.mouse_button(ev.pos)
        pygame.time.set_timer(pygame.USEREVENT, 0)
        return

# main
def main(argv):
    dirname = os.path.dirname(argv[0])
    pygame.mixer.pre_init(22050)
    pygame.init()
    pygame.display.set_mode((640,480))
    resource = Resource(os.path.join(dirname, 'resource'))
    surface = pygame.display.get_surface()
    game = PySame(resource, surface)
    game.start()
    return game.run()

if __name__ == '__main__': sys.exit(main(sys.argv))
