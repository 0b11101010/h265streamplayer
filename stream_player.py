#!/usr/bin/python3

'''
MIT License

Copyright (c) 2022 Erhan Akagündüz

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

from multiprocessing import Queue
from stream_receiver import StreamReceiver
import cv2
import numpy as np
import time

def getNoStreamImage():
    image = np.zeros((720, 1280, 3), np.uint8)
    image = cv2.putText(image, 'Video Stream is lost!', (0, 15), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0,255,0), 1, cv2.LINE_AA)
    return image

class Window:
    def __init__(self, name = 'H265 Stream Player'):
        self.windowName = name
        self.window = cv2.namedWindow(self.windowName, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)

    def getName(self) -> str:
        return self.windowName


if __name__ == '__main__':
    
    pipelineStr = (
            'udpsrc port=5000'
            ' ! application/x-rtp,media=video,clock-rate=90000,encoding-name=H265'
            ' ! rtph265depay'
            ' ! h265parse'
            ' ! queue max-size-buffers=8 max-size-bytes=55987200 leaky=2'
            ' ! video/x-h265,stream-format=(string)byte-stream,alignment=au'
            ' ! avdec_h265 max-threads=4 output-corrupt=false'
            ' ! videoconvert n-threads=4'
            ' ! video/x-raw,format=(string)BGR'
            ' ! queue max-size-buffers=8 max-size-bytes=55987200 leaky=2'
            ' ! appsink'
        ),

    imageQueue = Queue(maxsize=4)
    streamReceiver = StreamReceiver(*pipelineStr, imageQueue)
    streamReceiver.start()

    noStreamImage = getNoStreamImage()
    window = Window()
    windowName = window.getName()
    cv2.imshow(windowName, noStreamImage)

    streamLossTime = 2.5
    lastTimeStamp = 0

    fpsMeasurementTimeStamp = 0
    fpsCounter = 0
    fps = 0

    while True:
        
        if not streamReceiver.is_alive():
            print('Stream receiver is not alive!')
            print('Exiting...')
            break

        isNewImCap = False
        if not imageQueue.empty():
            try:
                image = imageQueue.get(timeout=0.010)
            
            except Queue.Empty:
                # Required if more than one thread gets image
                print('Queue.get error!')
            
            else:
                lastTimeStamp = time.monotonic()
                fpsCounter += 1
                isNewImCap = True
                
        
        now = time.monotonic()
        isStreamLost = (now - lastTimeStamp) > streamLossTime
        waitTime = 1
        if isStreamLost:
            image = noStreamImage
            waitTime = 50

        if (now - fpsMeasurementTimeStamp) > 0.999:
            fpsMeasurementTimeStamp = now
            fps = fpsCounter
            fpsCounter = 0
        
        if not isStreamLost and isNewImCap:
            image = cv2.putText(image, 'FPS : ' + str(fps), (0, 15), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0,255,0), 1, cv2.LINE_AA)
        
        cv2.imshow(windowName, image)
        
        key = cv2.waitKey(waitTime)
        if (key == ord('q')):
            streamReceiver.kill()
            break
