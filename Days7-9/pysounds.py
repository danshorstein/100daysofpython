import sys, os
import time, random 
import wave, argparse, pygame 
import numpy as np
from collections import deque
from matplotlib import pyplot as plt

# show plot of algorithm in action?
gShowPlot = False

# notes of a Pentatonic Minor scale
# piano C4-E(b)-F-G-B(b)-C5
pmNotes = {'C4': 262, 'Eb': 311, 'F': 349, 'G':391, 'Bb':466}

def writeWAVE(fname, data):
    # open file 
    file = wave.open(fname, 'wb')
    # WAV file parameters 
    nChannels = 1
    sampleWidth = 2
    frameRate = 44100
    nFrames = 44100
    # set parameters
    file.setparams((nChannels, sampleWidth, frameRate, nFrames,
                    'NONE', 'noncompressed'))
    file.writeframes(data)
    file.close()

def generateNote(freq):
    nSamples = 44100
    sampleRate = 44100
    N = int(sampleRate/freq)
    # initialize ring buffer
    buf = deque([random.random() - 0.5 for i in range(N)])
    # plot of flag set 
    if gShowPlot:
        axline, = plt.plot(buf)
    # init sample buffer
    samples = np.array([0]*nSamples, 'float32')
    for i in range(nSamples):
        samples[i] = buf[0]
        avg = 0.995*0.5*(buf[0] + buf[1])
        buf.append(avg)
        buf.popleft()  
        # plot of flag set 
        if gShowPlot:
            if i % 1000 == 0:
                axline.set_ydata(buf)
                plt.draw()
      
    # samples to 16-bit to string
    # max value is 32767 for 16-bit
    samples = np.array(samples * 32767, 'int16')
    return samples.tostring()

class NotePlayer:
    # constr
    def __init__(self):
        pygame.mixer.init(44100)
        pygame.init()
        # dictionary of notes
        self.notes = {}
        
    # add a note
    def add(self, fileName):
        self.notes[fileName] = pygame.mixer.Sound(fileName)
        
    # play a note
    def play(self, fileName):
        try:
            self.notes[fileName].play()
        except:
            print(fileName + ' not found!')
            
    def playRandom(self):
        """play a random note"""
        index = random.randint(0, len(self.notes)-1)
        note = list(self.notes.values())[index]
        note.play()

nplayer = NotePlayer()

print('creating notes...')
for name, freq in list(pmNotes.items()):
    fileName = name + '.wav' 
    if not os.path.exists(fileName):
        data = generateNote(freq) 
        print('creating ' + fileName + '...')
        writeWAVE(fileName, data) 
    else:
        print('fileName already created. skipping...')

    # add note to player
    nplayer.add(name + '.wav')

def main():

    
    # play a random tune
    if True:
        while True:
            try: 
                nplayer.playRandom()
                # rest - 1 to 8 beats
                rest = np.random.choice([1, 2, 4, 8], 1, 
                                        p=[0.15, 0.7, 0.1, 0.05])
                time.sleep(0.25*rest[0])
            except KeyboardInterrupt:
                exit()

    # random piano mode
    if True:
        while True:
            for event in pygame.event.get():
                if (event.type == pygame.KEYUP):
                    print("key pressed")
                    nplayer.playRandom()
                    time.sleep(0.5)
  
# call main
if __name__ == '__main__':
    main()
