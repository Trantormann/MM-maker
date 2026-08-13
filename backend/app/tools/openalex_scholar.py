"""OpenAlex 学术文献检索模块。"""

import httpx
from app.utils.log_util import logger


class OpenAlexScholar:
    """OpenAlex 学术文献检索器。"""

    def __init__(self, task_id: str, email: str, api_key: str | None = None):
        self.task_id = task_id
        self.email = email
        self.api_key = api_key
        self.base_url = "https://api.openalex.org"

    async def search_papers(self, query: str, limit: int = 5) -> list[dict]:
        """搜索学术文献。

        Args:
            query: 搜索关键词。
            limit: 返回结果数量。

        Returns:
            文献列表。
        """
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "search": query,
                    "per_page": limit,
                    "mailto": self.email,
                }
                if self.api_key:
                    params["api_key"] = self.api_key

                response = await client.get(
                    f"{self.base_url}/works",
                    params=params,
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()

                papers = []
                for work in data.get("results", []):
                    paper = {
                        "title": work.get("title", ""),
                        "authors": [
                            author.get("author", {}).get("display_name", "")
                            for author in work.get("authorships", [])
                        ],
                        "year": work.get("publication_year", ""),
                        "doi": work.get("doi", ""),
                        "citations": work.get("cited_by_count", 0),
                        "abstract": work.get("abstract", ""),
                    }
                    papers.append(paper)

                logger.info(f"OpenAlex 搜索完成: {len(papers)} 篇文献")
                return papers

        except Exception as e:
            logger.error(f"OpenAlex 搜索失败: {e}")
            return []

    def papers_to_str(self, papers: list[dict]) -> str:
        """将文献列表格式化为字符串。

        Args:
            papers: 文献列表。

        Returns:
            格式化后的字符串。
        """
        if not papers:
            return "未找到相关文献"

        lines = []
        for i, paper in enumerate(papers, 1):
            authors = ", ".join(paper["authors"][:3])
            if len(paper["authors"]) > 3:
                authors += " et al."
            lines.append(
                f"[{i}] {paper['title']}\n"
                f"    作者: {authors}\n"
                f"    年份: {paper['year']}, 引用: {paper['citations']}\n"
                f"    DOI: {paper['doi']}\n"
            )
        return "\n".join(lines)
