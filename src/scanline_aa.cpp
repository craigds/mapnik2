/* This file is part of Mapnik (c++ mapping toolkit)
 * Copyright (C) 2005 Artem Pavlenko
 *
 * Mapnik is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
 */

//  Credits:
//  I gratefully acknowledge the inspiring work of Maxim Shemanarev (McSeem), 
//  author of Anti-Grain Geometry (http://www.antigrain.com), and also the developers 
//  of the FreeType library (http://www.freetype.org). I have slightly modified the polygon 
//  rasterizing algorithm to work with my library, but render_line and 
//  render_hline remain intact. 

//$Id: scanline_aa.cpp 29 2005-04-01 14:30:11Z pavlenko $

#include "scanline_aa.hpp"

namespace mapnik
{

    inline void cell_aa::set_cover(int c, int a)
    {
        cover = c;
        area = a;
    }
    inline void cell_aa::add_cover(int c, int a)
    {
        cover += c;
        area += a;
    }
    inline void cell_aa::set_coord(int cx, int cy)
    {
        x = short(cx);
        y = short(cy);
        packed_coord = (cy << 16) + cx;
    }
    inline void cell_aa::set(int cx, int cy, int c, int a)
    {
        x = short(cx);
        y = short(cy);
        packed_coord = (cy << 16) + cx;
        cover = c;
        area = a;
    }

    outline_aa::~outline_aa()
    {
        delete [] m_sorted_cells;
        if(m_num_blocks)
        {
            cell_aa** ptr = m_cells + m_num_blocks - 1;
            while(m_num_blocks--)
            {
                delete [] *ptr;
                ptr--;
            }
            delete [] m_cells;
        }
    }

    outline_aa::outline_aa() :
	m_num_blocks(0),
        m_max_blocks(0),
        m_cur_block(0),
        m_num_cells(0),
        m_cells(0),
        m_cur_cell_ptr(0),
        m_sorted_cells(0),
        m_sorted_size(0),
        m_cur_x(0),
        m_cur_y(0),
        m_min_x(0x7FFFFFFF),
        m_min_y(0x7FFFFFFF),
        m_max_x(-0x7FFFFFFF),
        m_max_y(-0x7FFFFFFF),
        m_sorted(false)
    {
        m_cur_cell.set(0x7FFF, 0x7FFF, 0, 0);
    }

    void outline_aa::reset()
    {
        m_num_cells = 0;
        m_cur_block = 0;
        m_cur_cell.set(0x7FFF, 0x7FFF, 0, 0);
        m_sorted = false;
        m_min_x =  0x7FFFFFFF;
        m_min_y =  0x7FFFFFFF;
        m_max_x = -0x7FFFFFFF;
        m_max_y = -0x7FFFFFFF;
    }

    void outline_aa::allocate_block()
    {
        if(m_cur_block >= m_num_blocks)
        {
            if(m_num_blocks >= m_max_blocks)
            {
                cell_aa** new_cells = new cell_aa* [m_max_blocks + cell_block_pool];
                if(m_cells)
                {
                    memcpy(new_cells, m_cells, m_max_blocks * sizeof(cell_aa*));
                    delete [] m_cells;
                }
                m_cells = new_cells;
                m_max_blocks += cell_block_pool;
            }
            m_cells[m_num_blocks++] = new cell_aa [unsigned(cell_block_size)];
        }
        m_cur_cell_ptr = m_cells[m_cur_block++];
    }

    inline void outline_aa::add_cur_cell()
    {
        if(m_cur_cell.area | m_cur_cell.cover)
        {
            if((m_num_cells & cell_block_mask) == 0)
            {
                if(m_num_blocks >= cell_block_limit) return;
                allocate_block();
            }
            *m_cur_cell_ptr++ = m_cur_cell;
            ++m_num_cells;
            if(m_cur_cell.x < m_min_x) m_min_x = m_cur_cell.x;
            if(m_cur_cell.x > m_max_x) m_max_x = m_cur_cell.x;
        }
    }

    inline void outline_aa::set_cur_cell(int x, int y)
    {
        if(m_cur_cell.packed_coord != (y << 16) + x)
        {
            add_cur_cell();
            m_cur_cell.set(x, y, 0, 0);
        }
    }

    inline void outline_aa::render_hline(int ey, int x1, int y1, int x2, int y2)
    {
        int ex1 = x1 >> poly_base_shift;
        int ex2 = x2 >> poly_base_shift;
        int fx1 = x1 & poly_base_mask;
        int fx2 = x2 & poly_base_mask;

        int delta, p, first, dx;
        int incr, lift, mod, rem;

 
        if(y1 == y2)
        {
            set_cur_cell(ex2, ey);
            return;
        }

 
        if(ex1 == ex2)
        {
            delta = y2 - y1;
            m_cur_cell.add_cover(delta, (fx1 + fx2) * delta);
            return;
        }
        p = (poly_base_size - fx1) * (y2 - y1);
        first = poly_base_size;
        incr  = 1;

        dx = x2 - x1;

        if(dx < 0)
        {
            p     = fx1 * (y2 - y1);
            first = 0;
            incr  = -1;
            dx    = -dx;
        }

        delta = p / dx;
        mod   = p % dx;

        if(mod < 0)
        {
            delta--;
            mod += dx;
        }

        m_cur_cell.add_cover(delta, (fx1 + first) * delta);

        ex1 += incr;
        set_cur_cell(ex1, ey);
        y1  += delta;

        if(ex1 != ex2)
        {
            p     = poly_base_size * (y2 - y1 + delta);
            lift  = p / dx;
            rem   = p % dx;

            if (rem < 0)
            {
                lift--;
                rem += dx;
            }

            mod -= dx;

            while (ex1 != ex2)
            {
                delta = lift;
                mod  += rem;
                if(mod >= 0)
                {
                    mod -= dx;
                    delta++;
                }

                m_cur_cell.add_cover(delta, (poly_base_size) * delta);
                y1  += delta;
                ex1 += incr;
                set_cur_cell(ex1, ey);
            }
        }
        delta = y2 - y1;
        m_cur_cell.add_cover(delta, (fx2 + poly_base_size - first) * delta);
    }

    void outline_aa::render_line(int x1, int y1, int x2, int y2)
    {
        int ey1 = y1 >> poly_base_shift;
        int ey2 = y2 >> poly_base_shift;
        int fy1 = y1 & poly_base_mask;
        int fy2 = y2 & poly_base_mask;

        int dx, dy, x_from, x_to;
        int p, rem, mod, lift, delta, first, incr;

        dx = x2 - x1;
        dy = y2 - y1;

  
        if(ey1 == ey2)
        {
            render_hline(ey1, x1, fy1, x2, fy2);
            return;
        }
        incr  = 1;
        if(dx == 0)
        {
            int ex = x1 >> poly_base_shift;
            int two_fx = (x1 - (ex << poly_base_shift)) << 1;
            int area;

            first = poly_base_size;
            if(dy < 0)
            {
                first = 0;
                incr  = -1;
            }

            x_from = x1;

            delta = first - fy1;
            m_cur_cell.add_cover(delta, two_fx * delta);

            ey1 += incr;
            set_cur_cell(ex, ey1);

            delta = first + first - poly_base_size;
            area = two_fx * delta;
            while(ey1 != ey2)
            {

                m_cur_cell.set_cover(delta, area);
                ey1 += incr;
                set_cur_cell(ex, ey1);
            }

            delta = fy2 - poly_base_size + first;
            m_cur_cell.add_cover(delta, two_fx * delta);
            return;
        }

        p = (poly_base_size - fy1) * dx;

        first = poly_base_size;

        if(dy < 0)
        {
            p     = fy1 * dx;
            first = 0;
            incr  = -1;
            dy    = -dy;
        }

        delta = p / dy;
        mod   = p % dy;

        if(mod < 0)
        {
            delta--;
            mod += dy;
        }

        x_from = x1 + delta;
        render_hline(ey1, x1, fy1, x_from, first);

        ey1 += incr;
        set_cur_cell(x_from >> poly_base_shift, ey1);

        if(ey1 != ey2)
        {
            p     = poly_base_size * dx;
            lift  = p / dy;
            rem   = p % dy;

            if(rem < 0)
            {
                lift--;
                rem += dy;
            }
            mod -= dy;

            while(ey1 != ey2)
            {
                delta = lift;
                mod  += rem;
                if (mod >= 0)
                {
                    mod -= dy;
                    delta++;
                }

                x_to = x_from + delta;
                render_hline(ey1, x_from, poly_base_size - first, x_to, first);
                x_from = x_to;

                ey1 += incr;
                set_cur_cell(x_from >> poly_base_shift, ey1);
            }
        }
        render_hline(ey1, x_from, poly_base_size - first, x2, fy2);
    }

    void outline_aa::move_to(int x, int y)
    {
        if ( m_sorted ) reset();
        set_cur_cell(x >> poly_base_shift, y >> poly_base_shift);
        m_cur_x = x;
        m_cur_y = y;
    }

    void outline_aa::line_to(int x, int y)
    {
        render_line(m_cur_x, m_cur_y, x, y);
        m_cur_x = x;
        m_cur_y = y;
        m_sorted = false;
    }

    enum
    {
	qsort_threshold = 9
    };

    template <class T> static inline void swap_cells(T* a, T* b)
    {
        T temp = *a;
        *a = *b;
        *b = temp;
    }

    template <class T> static inline bool less_than(T* a, T* b)
    {
        return (*a)->packed_coord < (*b)->packed_coord;
    }

    void outline_aa::qsort_cells(cell_aa** start, unsigned num)
    {
        cell_aa**  stack[80];
        cell_aa*** top;
        cell_aa**  limit;
        cell_aa**  base;

        limit = start + num;
        base  = start;
        top   = stack;

        for (;;)
        {
            int len = int(limit - base);

            cell_aa** i;
            cell_aa** j;
            cell_aa** pivot;

            if(len > qsort_threshold)
            { 
                pivot = base + len / 2;
                swap_cells(base, pivot);

                i = base + 1;
                j = limit - 1;

                if(less_than(j, i))
                {
                    swap_cells(i, j);
                }

                if(less_than(base, i))
                {
                    swap_cells(base, i);
                }

                if(less_than(j, base))
                {
                    swap_cells(base, j);
                }

                for(;;)
                {
                    do i++; while( less_than(i, base) );
                    do j--; while( less_than(base, j) );

                    if ( i > j )
                    {
                        break;
                    }

                    swap_cells(i, j);
                }

                swap_cells(base, j);

                if(j - base > limit - i)
                {
                    top[0] = base;
                    top[1] = j;
                    base   = i;
                }
                else
                {
                    top[0] = i;
                    top[1] = limit;
                    limit  = j;
                }
                top += 2;
            }
            else
            {

                j = base;
                i = j + 1;

                for(; i < limit; j = i, i++)
                {
                    for(; less_than(j + 1, j); j--)
                    {
                        swap_cells(j + 1, j);
                        if (j == base)
                        {
                            break;
                        }
                    }
                }
                if(top > stack)
                {
                    top  -= 2;
                    base  = top[0];
                    limit = top[1];
                }
                else
                {
                    break;
                }
            }
        }
    }

    void outline_aa::sort_cells()
    {
        if(m_num_cells == 0) return;
        if(m_num_cells > m_sorted_size)
        {
            delete [] m_sorted_cells;
            m_sorted_size = m_num_cells;
            m_sorted_cells = new cell_aa* [m_num_cells + 1];
        }

        cell_aa** sorted_ptr = m_sorted_cells;
        cell_aa** block_ptr = m_cells;
        cell_aa*  cell_ptr;

        unsigned nb = m_num_cells >> cell_block_shift;
        unsigned i;

        while(nb--)
        {
            cell_ptr = *block_ptr++;
            i = cell_block_size;
            while(i--)
            {
                *sorted_ptr++ = cell_ptr++;
            }
        }

        cell_ptr = *block_ptr++;
        i = m_num_cells & cell_block_mask;
        while(i--)
        {
            *sorted_ptr++ = cell_ptr++;
        }
        m_sorted_cells[m_num_cells] = 0;
        qsort_cells(m_sorted_cells, m_num_cells);
        m_min_y = m_sorted_cells[0]->y;
        m_max_y = m_sorted_cells[m_num_cells - 1]->y;
    }

    const cell_aa* const* outline_aa::cells()
    {
        if(!m_sorted)
        {
            add_cur_cell();
            sort_cells();
            m_sorted = true;
        }
        return m_sorted_cells;
    }   

    template <typename PixBuffer>
    template <typename Transform>
    void ScanlineRasterizerAA<PixBuffer>::render(const geometry_type& geom,const Color& c)
    {
        reset();
        unsigned rgba=c.rgba();
        clip_box(0,0,pixbuf_->width(),pixbuf_->height());
        geometry_type::path_iterator<Transform> itr=geom.template begin<Transform>();
        while(itr!=geom.template end<Transform>())
        {
            if (itr->cmd == SEG_MOVETO)
            {
                move_to(itr->x,itr->y);
            }
            else if (itr->cmd == SEG_LINETO)
            {
                line_to(itr->x,itr->y);
            }
            ++itr;
        }

        if(rewind_scanlines())
        {
            scanline_u8 sl;
            sl.reset(min_x(),max_x());
            while(sweep_scanline(sl))
            {
                int y = sl.y();
                unsigned num_spans = sl.num_spans();
                typename scanline_u8::const_iterator span = sl.begin();
                do
                {
                    int x = span->x;
                    if(span->len>0)
                    {
                        blend_hline(x,span->len,y,span->covers,rgba);
                    }
                    ++span;
                } while(--num_spans);
            }
        }
    }
    template <typename PixBuffer>
    inline void ScanlineRasterizerAA<PixBuffer>::blend_hline(int x0,int len,int y,const unsigned char* covers,
							     unsigned rgba)
    {
        if (y<0) return;
        if (y>(int)pixbuf_->height()-1) return;
  
        if(x0<0)
        {
            len -= 0 - x0;
            if(len <= 0) return;
            covers += 0 - x0;
            x0 = 0;
        }
        if(x0 + len > (int)pixbuf_->width())
        {
            len = pixbuf_->width() - x0 + 1;
            if(len <= 0) return;
        }
        for(int x=x0;x<x0+len;x++)
        {
            int alpha = int(*covers++);
            pixbuf_->blendPixel(x,y,rgba,alpha);
        }
    }
    
    template <typename PixBuffer>
    inline void ScanlineRasterizerAA<PixBuffer>::render_hline(int x0,int x1,int y,unsigned rgba)
    {
        if (y < 0) return;
        if (y > (int)pixbuf_->height() - 1) return;
        if (x0 < 0) x0 = 0;
        if (x1 >(int)pixbuf_->width() - 1)  x1 = pixbuf_->width()-1;
        for(int x=x0;x<=x1;x++) pixbuf_->setPixel(x,y,rgba);
    }

    template class ScanlineRasterizerAA<Image32>;
    template void ScanlineRasterizerAA<Image32>::render<SHIFT8>(const geometry_type&,const Color&);
}
