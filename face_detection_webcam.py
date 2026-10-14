import cv2
import sys

def main():
    # Load the pre-trained Haar cascades for face detection from cv2.data (built-in path)
    face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(face_cascade_path)

    if face_cascade.empty():
        print("Error: Could not load the Haar cascade classifier XML file.")
        print("Make sure OpenCV is installed correctly.")
        sys.exit(1)

    # Open a connection to the first available webcam (index 0)
    cap = cv2.VideoCapture(0)

    # Check if we were able to successfully open the webcam
    if not cap.isOpened():
        print("Error: Could not open the webcam. Please make sure it is connected and not used by another application.")
        sys.exit(1)

    print("Webcam successfully opened.")
    print("Press 'q' inside the video window to quit.")

    while True:
        # Read a frame from the webcam
        ret, frame = cap.read()
        
        if not ret:
            print("Failed to grab a frame from the webcam.")
            break

        # Convert the frame to grayscale (Haar cascades work faster and evaluate patterns on single channel)
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces
        # scaleFactor=1.1: Reduces image size by 10% at each image scale
        # minNeighbors=5:  Specifies how many neighbors each candidate rectangle should have to retain it
        # minSize=(30,30): Minimum possible object size. Objects smaller than that are ignored.
        faces = face_cascade.detectMultiScale(
            gray_frame,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        # Draw a bounding box around the detected faces
        for (x, y, w, h) in faces:
            # Draw the rectangle
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            # Put label text above the bounding box
            cv2.putText(frame, 'Face Detected', (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Display the resulting frame
        cv2.imshow('Haar-like Feature Face Detection (Press q to exit)', frame)

        # Break the loop if the user presses 'q' key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Clean up: release the webcam and close all OpenCV windows
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
