export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const NOTION_KEY = process.env.NOTION_KEY;
  if (!NOTION_KEY) {
    return res.status(500).json({ error: 'NOTION_KEY not set' });
  }

  try {
    const body = {
      page_size: req.body.page_size || 100,
      sorts: req.body.sorts || [],
    };
    if (req.body.start_cursor) body.start_cursor = req.body.start_cursor;

    const response = await fetch(
      'https://api.notion.com/v1/databases/' + req.body.database_id + '/query',
      {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer ' + NOTION_KEY,
          'Content-Type': 'application/json',
          'Notion-Version': '2022-06-28'
        },
        body: JSON.stringify(body)
      }
    );

    const data = await response.json();
    return res.status(200).json(data);
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}