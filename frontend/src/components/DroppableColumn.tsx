import React from 'react';
import { useDroppable } from '@dnd-kit/core';

interface Props {
  id: string;
  title: string;
  children: React.ReactNode;
}

export const DroppableColumn = ({ id, title, children }: Props) => {
  const { setNodeRef } = useDroppable({ id });

  return (
    <div className="kanban-column" ref={setNodeRef}>
      <div className="kanban-column-header">
        {title}
        <span style={{ fontSize: '0.8rem', background: 'rgba(255,255,255,0.1)', padding: '2px 8px', borderRadius: '12px' }}>
          {React.Children.count(children)}
        </span>
      </div>
      <div className="kanban-column-body">
        {children}
      </div>
    </div>
  );
};
