适合AI系统的访问控制方法ReBAC:基于关系的访问控制

ReBAC是基于关系的访问控制（Relationship-Based Access Control)
由于大模型本身并无权限管理及访问控制的能力，但大模型需要处理数据，而数据需要访问控制，所以，基于大模型开发的系统，必须在外围增加访问控制的能力，以实现权限管理。
实现访问控制的方法有很多，传统的RBAC，ABAC等都可以实现，但以RAG为基础的系统，在处理大量文档时，需要在文档切片级进行权限控制，对实现的效率要求很高，RBAC及ABAC都不太合适，目前看国外很多厂商开始推出基于ReBAC的方法，是个更好的思路。
本文分三部分：
ReBAC介绍
ReBAC在RAG系统中的应用
Goolge的ReBAC实践及部分开源实现
全文约6000字，阅读需要15分钟。

1.ReBAC介绍
ReBAC这个术语是在2007年由Carrie Gates在她的论文《Access Control Requirements for Web 2.0 Security and Privacy》中正式创造的。2 019年Google发表了介绍"Zanzibar: Google's Consistent, Global Authorization System"的论文，这极大推动了ReBAC的普及。
ReBAC 是一个策略模型，专注于关系，即资源和身份（即用户）之间以及彼此之间的连接方式。这些连接用于实现授权，即确保正确的人员和服务拥有对正确资源的正确访问权限。ReBAC 是一种细粒度授权模型，可以替代其他常见授权模型，包括基于角色的访问控制 (RBAC)和 基于属性的访问控制 (ABAC)。
ReBAC是一种基于图的模型，有两个核心概念：关系元组（Relation Tuples）和用户集重写规则（Userset Rewrite），关系组只处理关系，增删改简单高效，而重写规则是一个通用规则（一般一个系统使用一个，比如Google像册，全系统统一规则），表达非常简单。
1.1关系元组（Relation Tuples）
ReBAC的核心是用关系元组来表示权限关系，格式为：
<对象>#<关系>@<用户>
1.2 用户集重写规则（Userset Rewrite）
可以定义关系之间的逻辑，比如：
所有者自动拥有编辑权限
编辑者自动拥有查看权限
父文件夹的查看者也能查看子文档

1.3 权限处理过程
以下图为例
图片

1.3.1关系主要包括两种
1)所有权关系 
folder:bob_files#owner@bob 
表示Bob是文件夹Bob’s Files的所有者，自然拥有所有权限。
2）父子关系 (层级结构) 
folder:bob_pics#parent@folder:bob_files 
folder:bob_pics#parent@folder:bob_files 
folder:bob_docs#parent@folder:bob_files 
file:1.jpg#parent@folder:bob_pics 
file:2.jpg#parent@folder:bob_pics 
file:cv.pdf#parent@folder:bob_docs 
file:data.xml#parent@folder:bob_docs
以第一条为例，bob_files 文件夹是Bob_pics的父节点，对Bob_files的所有权限，可用于bob_pics.
1.3.2 重写规则
以下权限规则定义了文件夹和文件的权限规则，直接拥有者有全部权限，查看者包括直接分配的查看者，拥有者自动拥有查看权限，也可以继续父文件夹的查看权限。文件则直接继承文件夹的相关权限。

文件夹权限配置

folder:
  relations:
    owner: {}  # 直接拥有者
    viewer:    # 查看者规则
      union:
        - this: {}                    # 直接分配的查看者
        - computed_userset:
            relation: "owner"         # 拥有者自动是查看者
        - tuple_to_userset:           # 继承父文件夹的查看权限
            tupleset:
              relation: "parent"
            computed_userset:
              relation: "viewer"

文件权限配置
file:
  relations:
    viewer:
      tuple_to_userset:               # 文件继承父文件夹权限
        tupleset:
          relation: "parent"
        computed_userset:
          relation: "viewer"

1.3.3 权限推导过程
查询：Bob能否查看 file:cv.pdf？
步骤1：查找父文件夹
file:cv.pdf#parent@folder:bob_docs
步骤2：检查父文件夹的查看权限
CHECK(bob, folder:bob_docs#viewer)
步骤3：应用文件夹的viewer重写规则
检查直接viewer关系：无
检查owner关系：需要找到 folder:bob_docs#owner@bob
检查父文件夹继承：folder:bob_docs#parent@folder:bob_files
步骤4：继续向上查找
CHECK(bob, folder:bob_files#viewer)
步骤5：在根文件夹找到所有权
folder:bob_files#owner@bob  ✓
步骤6：根据重写规则推导
bob is owner of folder:bob_files
→ bob is viewer of folder:bob_files  (owner包含viewer)
→ bob is viewer of folder:bob_docs   (继承规则)
→ bob is viewer of file:cv.pdf       (文件继承文件夹权限)
采用递归的方法查找，实现非常容易。
1.3.4 权限修改
单个元组修改

写入: doc:readme#viewer@alice  // 给Alice查看权限
删除: doc:readme#editor@bob    // 移除Bob的编辑权限
批量修改（读-修改-写）
1. 读取对象的所有关系元组，包括"锁"元组
2. 生成要写入或删除的元组
3. 提交修改，条件是锁元组未被其他人修改
4. 如果冲突，回到步骤1重试
1.4 组织
图片
ReBAC也有组织的概念，这个和RBAC的角色差不多。
传统的RBAC及ABAC的策略均采用关系数据库的方法，在处理策略时使用多表查询，效率较低，而ReBAC基于图的方法，使用图数据库，且策略修改非常方便，所以，效率非常高。
Google Zanzibar能够处理数万亿个访问控制列表和每秒数百万次的授权请求，支持数十亿人使用的各种服务。在三年的生产使用中，其保持了小于10毫秒的第95百分位延迟和大于99.999%的可用性。这是个非常理想的性能。

2.RAG中的实现方法

RAG是最典型的AI处理外部数据的方法，如何给RAG加访问控制是个非常迫切的问题。
先看一下RAG处理过程，见下图，预处理阶段，将原始文档作内容提取，分段，然后嵌入式编码，入向量库。在应用阶段，根据用户的查询，作嵌入式编码，然后从向量数据库中查到最符合查询要求的多个片段（比如Top10)，与用户的查询结合，送入大模型做内容生成。

图片
这个过程最大的问题是，用户会查询到向量库中的所有内容，这可能涉及到权限问题，比如，向量库中可能有财务信息，而一般员工不应该有财务信息的权限，这会导致越权及信息安全的问题。
那么，如何在这个系统上增加访问控制？
2.1  预处理阶段
在预处理阶段，对所有的数据作权限处理及关系处理。类似下图：

图片
一个文件或文件夹，一般要考虑两种权限，拥有者（完整权限）和查看者（只读权限），考虑到当前企业RAG的具体场景，完整权限一般由管理员完成，其它所有人都是只读权限，所以重点处理读权限。
读权限从根开始，也可能从某个文件夹或文件开始，基于父子关系继承，最后的分段chunck继承文档的权限。
按ReBAC的思想，首先需要处理所有权关系，按对象#viewer@用户及用户组，规则可以这样写
 folder:财务文件#viewer@财务部员工
然后处理父子关系
比如，a.doc与财务文件是父子关系，继承财务文件的权限，可以这样写
file:a.doc #parent@folder:财务文件
有了以上关系，基本可以确定访问权限
2.2 应用阶段
根据用户的身份来确定数据库检索出的信息是否有权限，无权限的抛弃掉。
完整流程如下图，橙色框为新增部分
图片
整体增加ReBAC系统，用于记录关系，权限等信息，以及提供对外的API（此部分可以参考开源，后边会介绍）
在预处理阶段，需要记录原始文件的权限（可能是直接权限或继承)，块的权限继承自文件，只记录关系即可，块应该有唯一的ID来标识。
用户在使用系统前需要登录，获取用户的ID，组ID等
在查询完成后，通过用户ID,块ID及关系，确定是否可读该内容，如果没有权限，即在查询结果中抛弃，不送入LLM中处理。
图中未标注系统管理部分，包括用户的管理及归属，权限变更等，这部分是标准化的方法。
上述功能完成，RAG即具备比较完整的权限管理。
RAG是典型的外部数据处理过程，其它应用，基本可以遵循类似的过程，在查询阶段加访问控制。

图片

3.Google的实现及一些开源
Google 在2019年发了论文《Zanzibar，谷歌一致的全球授权系统》，详细介绍了其ReBAC的原理和实现。其架构图如下：
图片
3.1 核心组件说明
1. 客户端层（Client）
左侧客户端：发送Check、Read、Expand、Write请求到ACL服务器集群
右侧客户端：通过Watch API监听ACL变更事件
2. Zanzibar服务集群
aclserver：主要服务器类型，处理所有核心ACL操作 
以集群形式组织，请求可到达任意服务器
服务器间通过内部RPC进行工作分发和结果聚合
实现分布式缓存和去重机制防止热点问题
watchserver：专门处理Watch请求的服务器 
监听changelog数据库
向客户端提供近实时的命名空间变更流
3. 存储层（Spanner全局数据库系统）
namespace configs
存储所有命名空间的配置信息
包含关系定义和userset重写规则
namespace 1...N relation tuples
每个客户端命名空间有独立的数据库
存储实际的关系元组数据
支持多版本存储以实现快照读取
changelog
跨所有命名空间的共享变更日志数据库
记录所有元组修改操作的时序历史
为Watch API提供数据源
4. 优化层
Leopard索引系统
专门优化大型嵌套集合的计算
通过Watch API监听ACL数据变更
提供优化的集合操作计算能力
读取命名空间快照进行离线索引构建
周期性离线管道
生成已知快照时间戳的命名空间转储
执行垃圾回收等维护任务

3.2 对外接口
Zanzibar通过RPC的形式提供API,主要是五个：
1. Read API - 读取关系元组
用途：客户端读取关系元组以显示ACL或组成员身份
2. Write API - 修改关系元组
支持两种写入模式：单元组修改和对象级修改
3. Check API - 授权检查
用途：确定是否具备操作权限
4. Watch API - 监听变更
5. Expand API - 展开有效userset
功能：返回给定 ⟨object#relation⟩ 对的有效userset
通过以上设计，简洁的API让客户端调用非常容易，大规模的部署冗余确保性能及可靠性,尤其是cache的支持，大幅提升了可靠性。
3.3 开源实现
由于Goolge Zanzibar的成功，国外已经有许多开源实现。
SpiceDB
SpiceDB 是一个开源授权数据库，与 Google Zanzibar 的设计原则非常相似，由Authzed发布维护。
https://github.com/authzed/spicedb
主要特点：
具有内置一致性保证的基于模式的建模
多后端支持（PostgreSQL、CockroachDB、Spanner）
通过 Watch API 实时更新权限
其应用加构
图片

2.Permify
Permify 专注于多租户场景和开发人员体验，就是由Permify这个公司维护的。
https://github.com/Permify/permify
主要特点：
专为多租户应用程序构建
自定义模式建模语言
实时权限更新
服务架构如下图
图片
3.OpenFGA
https://github.com/openfga
OpenFGA是Linux基金会的，就是模仿Google  Zanzibar的，在保持高性能的同时优先考虑开发人员的体验。
主要特点：
用户友好的建模语言和可视化工具
存储和计算的双 API 系统
通过缓存进行快速授权检查
下图是他们给的应用权限架构
图片

4. Warrant
Warrant是一种开源、高度可扩展、集中式、细粒度的授权服务，用于定义、存储、查询、检查和审计应用程序授权模型和访问规则。由WARRANT公司维护
https://github.com/warrant-dev/warrant
从本质上讲，Warrant 是一个基于关系的访问控制 (ReBAC) 引擎（受 Google Zanzibar 启发），能够执行任何授权范例，包括基于角色的访问控制 (RBAC)、基于属性的访问控制 (ABAC) 和基于关系的访问控制 (ReBAC)。
主要特点：
用于管理授权模型、访问规则和其他 Warrant 资源的 HTTP API
实时、低延迟 API，用于在运行时在应用程序中执行访问检查
与内部和第三方身份提供商集成
官方支持流行语言和框架的 SDK（后端和前端）
支持多种数据库，包括：MySQL、Postgres 和 SQLite（内存或文件）
5. Ory Keto
https://github.com/ory
Ory Keto 提供面向微服务的 Zanzibar 实现，由https://www.ory.sh/keto 维护。主要特点：
微服务优先架构
支持 DSL 的 YAML 配置
HTTP/gRPC API 灵活性
3.4 AWS对ReBAC的支持。
AWS目前有多种服务能够支持ReBAC,也支持多种ReBAC服务，整体架构见下图，对三方的支持在左下角。其中OKTA未找到开源。
图片
https://aws.amazon.com/cn/blogs/database/graph-powered-authorization-relationship-based-access-control-for-access-management/
4.总结
对当今几乎所有IT系统来说，访问控制都是基本的安全手段。好的访问控制方法需要简单，高效。
而ReBAC从设计思想和Google的实践来看，都非常好地满足大规模系统和应用，AWS对该种方法也支持非常到位，说明它确实有独到之处。
AI系统的权限管理，也已经有了非常多的ReBAC的用例，这种方法，值得AI应用系统开发者认真考虑。

