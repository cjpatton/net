.PHONY: all assets html pdf tex blog clean

all: assets pdf html blog

assets:
	mkdir -p public
	cp -R static/. public/

html: gen_resume.py resume.toml t.index.html
	python3 gen_resume.py html resume.toml t.index.html public/index.html

blog: gen_blog.py t.blog.html t.post.html t.blog-header.html $(wildcard blog/*)
	python3 gen_blog.py

pdf: tex
	pdflatex cv.tex
	mkdir -p public
	mv cv.pdf public/cv.pdf

tex: gen_resume.py resume.toml t.cv.tex
	python3 gen_resume.py tex resume.toml t.cv.tex cv.tex

clean:
	rm -f *.out *.log *.aux *.pdf
	rm -rf public
