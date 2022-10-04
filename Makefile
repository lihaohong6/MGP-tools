.PHONY: build template clean cleanall
build:
	pyinstaller -F user_contrib.py

template:
	pyinstaller -F vocaloid_producer_template.py

clean:
	rm -rf build
	rm -f *.spec

cleanall:
	rm -rf build dist
	rm -f *.spec