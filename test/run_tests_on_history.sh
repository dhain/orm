set -e

git rev-list --reverse HEAD | while read rev; do
    echo "Checking out: $(git log --oneline -1 $rev)";
    git checkout -q $rev;
    find . -name "*.pyc" -exec rm \{\} \;;
    python test/run_tests.py all;
done
