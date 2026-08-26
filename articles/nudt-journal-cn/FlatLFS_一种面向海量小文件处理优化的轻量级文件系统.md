# FlatLFS:一种面向海量小文件处理优化的轻量级文件系统

Published: 2012-04-05 00:00:00

Source: http://journal.nudt.edu.cn/gfkjdxxb/article/abstract/201302022?tab=abstract

海量小文件的高效存储和访问是当前分布式文件系统面临的主要挑战之一。以GFS和HDFS为代表的分布式文件系统大多面向海量大文件的高效存储和访问设计，缺乏小文件处理的针对性优化，导致访问海量小文件时效率低下。针对分布式文件系统中海量小文件访问时的数据服务器优化问题，提出了一种采用扁平式数据存储方法的轻量级文件系统FlatLFS，取代传统文件系统对上层分布式文件系统提供数据存储和访问支持，提高了数据服务器处理小数据块时的I/O性能，从而提升了整个分布式文件系统的性能。实验表明，当数据块大小设定为1M时，FlatLFS的随机读性能分别比ext3、ext4、reiserfs高135%、112%和122%。

The storage and access of massive small files are one of the challenges in the design of DFS(Distributed file system). Most of the DFSs, such as GFS and HDFS, are designed for handling massive big files. The performance of DFSs decreases greatly when accessing massive small files without special optimization for small files. This research focuses on the optimizing of the performance of data server in handling massive small files, and presents a Flat Lightweight File System called FlatLFS in which the user data are managed flat in disks. FlatLFS is supposed to substitute the traditional file system when accessing user data for upper DFSs. With the improvement of the performance of small data block processing on data servers by FlatLFS, the performance of the whole DFSs is greatly improved. The effectiveness of FlatLFS is proved with intensive experiments: when the size of data block is 1M, the performance of random read of FlatLFS is 135%, 112% and 122% higher than ext 3 ,ext4 and reiserfs respectively. 

付松龄,廖湘科,黄辰林,等. FlatLFS:一种面向海量小文件处理优化的轻量级文件系统[J].国防科技大学学报,2013,35(2):120-126. FU Songling, LIAO Xiangke, HUANG Chenlin, et al. FlatLFS: a lightweight file system for optimizing the performance of accessing massive small files[J]. Journal of National University of Defense Technology,2013,35(2):120-126.
