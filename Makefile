all: pdf html

html: gen.py resume.json t.index.html
	python2.7 gen.py html resume.json t.index.html web/index.html

pdf: tex
	pdflatex cv.tex
	mv cv.pdf web/cv.pdf

tex: gen.py resume.json t.cv.tex
	python2.7 gen.py tex resume.json t.cv.tex cv.tex

clean:
	rm -f *.out *.log *.aux *.pdf
