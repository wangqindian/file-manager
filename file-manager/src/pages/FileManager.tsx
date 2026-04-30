import { useState, useEffect } from "react";
import { Container, Breadcrumb, Row, Col, Table, Button, Modal, Spinner } from "react-bootstrap";

interface FileItem {
  id: string;
  name: string;
  type: "file" | "folder";
  size?: number;
  parent_id: string | null;
  created_at: string;
  modified_at: string;
  path?: string;
}

const API_BASE = "/api";

export default function FileManager() {
  const [currentFolderId, setCurrentFolderId] = useState<string | null>(null);
  const [currentFolderName, setCurrentFolderName] = useState<string>("Home");
  const [files, setFiles] = useState<FileItem[]>([]);
  const [folders, setFolders] = useState<FileItem[]>([]);
  const [pathStack, setPathStack] = useState<{ id: string | null; name: string }[]>([
    { id: null, name: "Home" },
  ]);
  const [showNewFolderModal, setShowNewFolderModal] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadContents();
  }, [currentFolderId]);

  const loadContents = async () => {
    setLoading(true);
    try {
      const filesUrl = currentFolderId
        ? `${API_BASE}/files?parent_id=${currentFolderId}`
        : `${API_BASE}/files`;
      const foldersUrl = currentFolderId
        ? `${API_BASE}/folders?parent_id=${currentFolderId}`
        : `${API_BASE}/folders`;

      const [filesRes, foldersRes] = await Promise.all([
        fetch(filesUrl),
        fetch(foldersUrl),
      ]);

      const filesData = await filesRes.json();
      const foldersData = await foldersRes.json();

      setFiles(Array.isArray(filesData) ? filesData : []);
      setFolders(Array.isArray(foldersData) ? foldersData : []);
    } catch (error) {
      console.error("Failed to load contents:", error);
      setFiles([]);
      setFolders([]);
    }
    setLoading(false);
  };

  const formatSize = (bytes?: number) => {
    if (!bytes) return "-";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  const navigateToFolder = async (folderId: string, folderName: string) => {
    setPathStack([...pathStack, { id: folderId, name: folderName }]);
    setCurrentFolderId(folderId);
    setCurrentFolderName(folderName);
  };

  const navigateToBreadcrumb = (index: number) => {
    const target = pathStack[index];
    setPathStack(pathStack.slice(0, index + 1));
    setCurrentFolderId(target.id);
    setCurrentFolderName(target.name);
  };

  const goHome = () => {
    setPathStack([{ id: null, name: "Home" }]);
    setCurrentFolderId(null);
    setCurrentFolderName("Home");
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;

    try {
      const res = await fetch(`${API_BASE}/folders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newFolderName,
          parent_id: currentFolderId,
        }),
      });

      if (res.ok) {
        setNewFolderName("");
        setShowNewFolderModal(false);
        loadContents();
      }
    } catch (error) {
      console.error("Failed to create folder:", error);
    }
  };

  const handleDeleteFolder = async (folderId: string) => {
    if (!confirm("确定要删除这个文件夹吗？")) return;

    try {
      const res = await fetch(`${API_BASE}/folders/${folderId}`, {
        method: "DELETE",
      });

      if (res.ok) {
        loadContents();
      }
    } catch (error) {
      console.error("Failed to delete folder:", error);
    }
  };

  const handleDeleteFile = async (fileId: string) => {
    if (!confirm("确定要删除这个文件吗？")) return;

    try {
      const res = await fetch(`${API_BASE}/files/${fileId}`, {
        method: "DELETE",
      });

      if (res.ok) {
        loadContents();
      }
    } catch (error) {
      console.error("Failed to delete file:", error);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    if (currentFolderId) {
      formData.append("parent_id", currentFolderId);
    }

    try {
      const res = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        loadContents();
      }
    } catch (error) {
      console.error("Failed to upload file:", error);
    }

    e.target.value = "";
  };

  const currentPath = pathStack.map((p) => p.name).join(" / ");

  return (
    <Container className="mt-4">
      <Row className="mb-3 align-items-center">
        <Col>
          <h4>当前路径: /{currentPath}</h4>
        </Col>
        <Col xs="auto">
          <Button variant="outline-secondary" onClick={goHome} className="me-2">
            返回主页
          </Button>
          <label className="btn btn-success me-2 mb-1">
            上传文件
            <input
              type="file"
              style={{ display: "none" }}
              onChange={handleFileUpload}
            />
          </label>
          <Button variant="primary" onClick={() => setShowNewFolderModal(true)}>
            新建文件夹
          </Button>
        </Col>
      </Row>

      <Breadcrumb className="mb-3">
        {pathStack.map((item, index) => (
          <Breadcrumb.Item
            key={index}
            active={index === pathStack.length - 1}
            onClick={() => navigateToBreadcrumb(index)}
            style={{ cursor: "pointer" }}
          >
            {item.name}
          </Breadcrumb.Item>
        ))}
      </Breadcrumb>

      {loading ? (
        <div className="text-center my-5">
          <Spinner animation="border" />
        </div>
      ) : folders.length === 0 && files.length === 0 ? (
        <p className="text-muted">文件夹为空</p>
      ) : (
        <Table striped bordered hover responsive>
          <thead>
            <tr>
              <th>名称</th>
              <th>类型</th>
              <th>大小</th>
              <th>修改日期</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {folders.map((folder) => (
              <tr key={folder.id}>
                <td>
                  <span
                    style={{ cursor: "pointer", color: "#0d6efd" }}
                    onClick={() => navigateToFolder(folder.id, folder.name)}
                  >
                    {folder.name}
                  </span>
                </td>
                <td>文件夹</td>
                <td>-</td>
                <td>{folder.modified_at?.split("T")[0]}</td>
                <td>
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => handleDeleteFolder(folder.id)}
                  >
                    删除
                  </Button>
                </td>
              </tr>
            ))}
            {files.map((file) => (
              <tr key={file.id}>
                <td>{file.name}</td>
                <td>文件</td>
                <td>{formatSize(file.size)}</td>
                <td>{file.modified_at?.split("T")[0]}</td>
                <td>
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => handleDeleteFile(file.id)}
                  >
                    删除
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal show={showNewFolderModal} onHide={() => setShowNewFolderModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>新建文件夹</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <input
            type="text"
            className="form-control"
            placeholder="输入文件夹名称"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
          />
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowNewFolderModal(false)}>
            取消
          </Button>
          <Button variant="primary" onClick={handleCreateFolder}>
            创建
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  );
}