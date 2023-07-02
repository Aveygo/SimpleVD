import dbm, os, pickle
import numpy as np

class Point:
    def __init__(self, position:np.ndarray, _id:bytes|None=None, children_ids:list[bytes]=[], num_children:int=0):
        self.position:np.ndarray = position
        self._id:bytes = _id if not _id is None else os.urandom(16)
        self.children_ids:list[bytes] = children_ids
        self.num_children:int = num_children

class Tree:
    def __init__(self, db_src:str, vec_shape:tuple, max_leafs:int=8):
        assert type(vec_shape) == tuple, "vec_shape must be tuple!"
        assert max_leafs > 1, "max_leafs must be greator than one!"
        
        self.db = dbm.open(db_src, 'c')
        self.root_name = b"root"
        
        self.vec_shape = vec_shape
        self.max_leafs = max_leafs

        if not self.root_name in self.db:
            self.db[self.root_name] = pickle.dumps(Point(np.zeros(vec_shape), self.root_name))
        else:
            db_shape = pickle.loads(self.db[self.root_name]).position.shape
            assert db_shape == self.vec_shape, f"Database vector mismatch: provided {vec_shape} vs database {db_shape}"
    
    @property
    def num_children(self):
        return pickle.loads(self.db[self.root_name]).num_children - self.max_leafs

    def find_path(self, point:Point, path:list[list[Point]]=None) -> list[list[Point]]:
        """
        Returns the path of nodes to get to the closest points
        eg:
        [
            [root],
            [layer_0 nodes sorted by distance],
            [layer_1 nodes sorted by distance],
            ...
            [layer_n nodes sorted by distance],
            [final points sorted by distance]
        ]

        max size = log(num_points, MAX_LEAFS) * MAX_LEAFS * VEC_LEN
        """
        if path is None:
            path = [[pickle.loads(self.db[self.root_name])]]

        if len(path[-1]) == 0 or len(path[-1][0].children_ids) == 0:
            return path
        
        children:list[Point] = []
        for child_id in path[-1][0].children_ids:
            children.append( pickle.loads(self.db[child_id]) )
        
        scores = [(np.linalg.norm(point.position - child.position), child) for child in children]
        scores.sort(key=lambda x: x[0])
        path.append([i[1] for i in scores])
        
        return self.find_path(point, path)
    
    def update_centers(self, path:list[list[Point]]=[]):
        """
        Bubble the new centers up the path.
        """
        if len(path) >= 2:
            center = np.array([i.position for i in path[-1]]).mean(axis=0)
            parent = path[-2][0]
            parent.position = center
            parent.num_children += 1
            self.db[parent._id] = pickle.dumps(parent)
            del path[-1]
            self.update_centers(path)
        
    def find_points(self, p:Point, number:int=1, path:list[list[Point]]|None=None):
        """
        Find number amount of points sorted by distance to point p
        """

        while True:
            path = self.find_path(p, path)
            if len(path) == 1:
                # Only root node found, no more points...
                return
            
            # Yield current points
            for point in path[-1]:
                if number > 0:
                    number -= 1
                    yield point
                else:
                    return
            
            del path[-1]
            del path[-1][0]

    def add_point(self, p:Point):
        """
        Add a point to the database
        """
        assert p.position.shape == self.vec_shape, f"Point shape mismatch: provided {p.position.shape} vs database {self.vec_shape}"
        
        path = self.find_path(p)

        if len(path) == 1:
            parent = path[-1][0]
            path.append([p])
        else:
            path[-1].insert(0, p)
            parent = path[-2][0]
        
        parent.children_ids.append(p._id)
        parent.num_children += 1
        self.db[p._id] = pickle.dumps(p)

        if len(path[-1]) >= self.max_leafs:
            for point in path[-1]:    
                moved_point = Point(point.position)
                point.children_ids = [moved_point._id]
                point.num_children = 1

                self.db[moved_point._id] = pickle.dumps(moved_point)
                self.db[point._id] = pickle.dumps(point)
            
        self.update_centers(path)

if __name__ == "__main__":
    import cv2, time

    t = Tree('main', (2,), 25)

    node_colors = {}
    width = 100
    height = 100

    print("Adding points to tree...")
   
    a = time.time()
    num = 1000
    for i in range(num):
        print(f"{i/num*100:.2f}%", end="\r")
        p = Point(np.random.randn(2))
        t.add_point(p)

    print(f"Points/sec = {num/(time.time() - a):.2f}")
    print(f"Root has {t.num_children} total children")

    query = Point([0, 0])
    result = []
    a = time.time()
    for point in t.find_points(query, 100):
        result.append(str(np.linalg.norm(point.position - query.position)))
    
    print(f"Found {len(result)} results in {time.time() - a:.4f} seconds")

    print("Distances:")
    print("\n".join(result[:10]))

    print("Rendering regions...")
    image = np.zeros((width, height, 3))
    for x in range(width):
        for y in range(height):
            print(f"{ (x*width + y) / (width*height) * 100 :.2f}%", end="\r")

            p = Point([
                ((x/width)-0.5)*2*3,
                ((y/height)-0.5)*2*3 
            ])

            r = t.find_path(p)

            if not r[-2][0]._id in node_colors:
                node_colors[r[-2][0]._id] = np.random.rand(3).tolist()
            
            image[x, y] = node_colors[r[-2][0]._id]

    cv2.imwrite(f"regions.png", (image*255).astype(np.uint8))
