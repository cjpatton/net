all: pdf html

html: gen.py resume.json t.index.html
	python3 gen.py html resume.json t.index.html public/index.html

pdf: tex
	pdflatex cv.tex
	mv cv.pdf public/cv.pdf

tex: gen.py resume.json t.cv.tex
	python3 gen.py tex resume.json t.cv.tex cv.tex

clean:
	rm -f *.out *.log *.aux *.pdf
