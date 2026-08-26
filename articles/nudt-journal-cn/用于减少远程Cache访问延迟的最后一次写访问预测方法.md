# 用于减少远程Cache访问延迟的最后一次写访问预测方法

Published: 2014-06-11 00:00:00

Source: http://journal.nudt.edu.cn/gfkjdxxb/article/abstract/201501003?tab=abstract

国家自然科学基金资助项目（61202119）；国家863计划资助项目(2013AA014301)

为减少远程Cache访问延迟，提高共享存储系统的性能，提出了一种新的基于程序内在写突发特性的最后一次写访问预测方法，并对一个具体的目录协议进行了改造，以支持该预测方法。通过预测Cache块的最后一次写访问并提前对其进行降级，处理器能直接从主存中读取数据，从而减少了远程Cache访问所需的一个网络跳步数。与当前基于指令的预测方法相比，该方法能极大减少存储开销。基准测试程序的评测结果表明，该方法能获得83.1%的预测准确率，并且能提高8.57%的程序执行性能，同时与基于指令的预测方法相比，该方法能分别减少历史踪迹表69%的存储开销和签名表36%的存储开销。

To reduce remote cache transfer latency and improve the performance of shared memory systems, a new last-write-touch prediction scheme that exploits the inherent write characteristics of a program is proposed and a directory protocol to support the scheme is adapted. By predicting a last-write-touch and self downgrading a cache block in advance, a processor can get the data from the memory directly and one network hop can be saved for a remote cache access. Compared with the existing instruction-based prediction technique, much storage overhead can be reduced. Experimental results show that it can achieve an average prediction accuracy of 83.1%, leading to improvements up to average 8.57% on the final application performance. Moreover, compared with the instruction-based prediction scheme, the scheme can reduce the storage overheads of the history table by 69% and the storage overheads of the signature table by 36%.

夏军,徐炜遐,庞征斌,等.用于减少远程Cache访问延迟的最后一次写访问预测方法[J].国防科技大学学报,2015,37(1):14-20. XIA Jun, XU Weixia, PANG Zhengbin, et al. A last-write-touch prediction scheme used to reduce remote Cache miss latency[J]. Journal of National University of Defense Technology,2015,37(1):14-20.
