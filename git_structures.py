from datetime import datetime
from gql_queries import ReadComments
import helper

issue_title_template = "# {title} [#{number}]({link})\n"

issue_template = """
`{author}` {status} this issue on {date}
{body}


"""

comment_template = """
`{author}` {status} this [comment]({link}) on {date}
{body}

"""


class ModifiableItem:
    def __init__(self, graphqlResult: dict):
        self.editor = graphqlResult["editor"]["login"] if graphqlResult["editor"] else None
        self.edit_at = helper.convertToDateTime(graphqlResult["lastEditedAt"]) if graphqlResult["lastEditedAt"] else None
        self.author = graphqlResult["author"]["login"]
        self.created_at = helper.convertToDateTime(graphqlResult["createdAt"])

    @property
    def is_modified(self):
        return self.editor != None

    @property
    def last_change_date(self) -> datetime:
        return self.edit_at if self.is_modified else self.created_at

    @property 
    def last_change_author(self) -> str:
        return self.editor if self.is_modified else self.author
    
    def get_status_str(self, time_range: tuple[datetime, datetime]) -> str:
        ret = []
        if self.created_at >= time_range[0] and self.created_at <= time_range[1]:
            ret.append("created")
        if self.edit_at and self.edit_at >= time_range[0] and self.edit_at <= time_range[1]:
            ret.append("modified")
        return " and ".join(ret) if ret else "deleted"

    def within_time_range(self, time_range: tuple[datetime, datetime]) -> bool:
        return self.last_change_date >= time_range[0] and self.last_change_date <= time_range[1]

class GitComment(ModifiableItem):
    def __init__(self, graphqlResult: dict, time_range: tuple[datetime, datetime]):
        super().__init__(graphqlResult)
        self.source_link = graphqlResult["url"]
        self.body = graphqlResult["body"]
        self.time_range = time_range

    def to_markdown(self):
        return comment_template.format(
                author=self.last_change_author,
                link=self.source_link,
                date=helper.format_date(self.last_change_date),
                body=helper.trim_and_format(self.body),
                status=self.get_status_str(self.time_range)
            )
    
    @property
    def is_deleted(self) -> bool:
        return self.body == None

class GitIssue(ModifiableItem):
    def __init__(self, graphqlResult: dict, timeRange: tuple[datetime, datetime]):
        super().__init__(graphqlResult)
        self.url = graphqlResult["url"]
        self.number = graphqlResult["number"]
        self.time_range = timeRange
        self.title = graphqlResult["title"]
        self.id = graphqlResult["id"]
        self.body = graphqlResult["body"]
        self.comments = []
        self.comments_query = ReadComments(self.id)
        
        self.read_paginated_comments(graphqlResult)

    def read_paginated_comments(self, graphqlResult:dict):
        self.last_comment_cursor = graphqlResult["comments"]["pageInfo"]["endCursor"] or "null"
        self.has_more_comments = graphqlResult["comments"]["pageInfo"]["hasNextPage"]

        for raw_comment in graphqlResult["comments"]["nodes"]:
            comment = GitComment(raw_comment, self.time_range)
            if comment.within_time_range(self.time_range) and not comment.is_deleted:
                self.comments.append(comment)
    
    def draft_gql_query(self) -> str:
        return self.comments_query.partial_query(self.url, self.last_comment_cursor)

    @property
    def has_more_data(self) -> bool:
        return self.has_more_comments
    
    @property
    def total_changes(self) -> int:
        return len(self.comments) + self.within_time_range(self.time_range)
    
    def to_markdown(self) -> str:
        header = issue_title_template.format(
            title = self.title,
            number = self.number,
            link = self.url)
        if self.within_time_range(self.time_range):
            temp = issue_template
            header += temp.format(
                author=self.last_change_author,
                date=helper.format_date(self.last_change_date),
                status=self.get_status_str(self.time_range),
                body=helper.trim_and_format(self.body)
            )
        self.comments.sort(key=lambda x: x.last_change_date)
        return header + '\n'.join([comment.to_markdown() for comment in self.comments])
