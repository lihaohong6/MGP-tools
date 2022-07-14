.PHONY: build clean
build:
	pyinstaller -F user_contrib.py

clean:
	rm -rf dist build
	rm -f *.spec