# SimpleVD
<p align="center">
  <img width="300" height="300" src="https://github.com/Aveygo/SimpleVD/blob/main/regions_high_res.png?raw=true">
</p>
A simple vector database written in python. Stores and sorts embeddings with good enough performance.

## Usage
```python
from main import Tree, Point

db = Tree("main.db", (2,))
p = Point([0, 0])

db.add_point(p)

for result in db.find_points(p):
  print(result.position)
```

## Results
```
10000 elements
Average write: 38.83 points/second
Average query (closest point): 4.0 ms
Average query (closest 100 points): 34.1 ms
```

The reason that the write speed is so slow is that each node only stores it's own position. This means that the database makes max_leafs extra reads than it has to when adding a point.
I've already implemented the solution, but for simplicity (and reducing database size) I have just left it as is.

## Main Drawback
The only issue currently is that the default find_points method priorities the distances to node centers, rather than the points themselves.
This means the returned points may not the be in the most optimal order, but rather just close enough.

eg:

```
Distances to query:
0.07842338060721434
0.06781609476418735
0.08850322869897881
0.11149906561095708
0.09001303738645108
0.10698424320139041
0.10763399773217425
0.10860402282732019
0.11588568022790191
0.10207879429688035
```

The fix is to read in a bunch of other points, sort them all, then use the sorted list as the result. But then again, it's still "good enough" for most applications.

## Conclusion
This is an experimental project to learn about vector databases. It works, has some improvements that can be made, but overall was just a learning experience.

